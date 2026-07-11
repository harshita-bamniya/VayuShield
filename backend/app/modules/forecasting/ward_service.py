"""Ward-level hyperlocal 72h AQI forecasting.

Algorithm per ward:
1. Pull last 7 days of hourly AQI from stations in this ward → diurnal baseline.
2. Pull last 24h trend for this ward.
3. Fetch Open-Meteo 72h hourly wind+temp forecast for city lat/lon.
4. Compute emission-source proximity score for this ward (from station centroid).
5. For each of 72 future hours:
     base      = ward diurnal_mean[hour_of_day]
     trend_adj = ward slope × h × damping
     wind_adj  = per-hour wind from Open-Meteo (instead of a single current value)
     src_adj   = ±offset based on dominant source proximity and wind direction
     predicted = clamp(1, 500, round((base + trend_adj) * wind_adj + src_adj))
"""

import math
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forecasting import repository as repo
from app.modules.forecasting.models import Forecast
from app.modules.forecasting.schemas import ForecastPointOut, ForecastRunOut
from app.modules.forecasting.service import _aqi_to_pm25, _linear_slope

MODEL_VERSION = "ward-hyperlocal-v1"
HORIZON_HOURS = 72
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def _fetch_open_meteo(lat: float, lon: float) -> list[dict]:
    """Fetch 72h hourly wind_speed + wind_direction + temperature from Open-Meteo.

    Returns list of dicts keyed by ISO timestamp, length ≥ 72.
    Falls back to empty list on any network error.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "wind_speed_10m,wind_direction_10m,temperature_2m",
                    "forecast_days": 4,
                    "timezone": "UTC",
                    "wind_speed_unit": "ms",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            speeds = hourly.get("wind_speed_10m", [])
            dirs = hourly.get("wind_direction_10m", [])
            temps = hourly.get("temperature_2m", [])
            return [
                {"time": times[i], "wind_speed": speeds[i], "wind_dir": dirs[i], "temp": temps[i]}
                for i in range(len(times))
            ]
    except Exception:
        return []


def _wind_adj(wind_speed: float | None) -> float:
    """Convert wind speed (m/s) to a dispersion multiplier [0.5, 1.3]."""
    if wind_speed is None:
        return 1.0
    return max(0.5, min(1.3, 1.0 - 0.04 * wind_speed))


def _bearing_diff(source_bearing: float, wind_dir: float) -> float:
    """Angular difference [0, 180] between source bearing and wind direction."""
    diff = abs(source_bearing - wind_dir) % 360
    return min(diff, 360 - diff)


def _source_proximity_offset(
    ward_lat: float,
    ward_lon: float,
    sources: list[dict],
    wind_dir: float | None,
) -> float:
    """Return an AQI offset (-10 to +15) based on upwind emission sources near the ward.

    Sources blowing toward the ward (±45° of wind direction) add weight.
    Sources far away (>5km) are discounted.
    """
    if not sources:
        return 0.0

    total_weight = 0.0
    for src in sources:
        src_lat = src.get("lat")
        src_lon = src.get("lon")
        src_type = src.get("type", "other")
        if src_lat is None or src_lon is None:
            continue

        # Haversine distance in km
        dlat = math.radians(src_lat - ward_lat)
        dlon = math.radians(src_lon - ward_lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(ward_lat)) * math.cos(math.radians(src_lat)) * math.sin(dlon / 2) ** 2
        dist_km = 6371 * 2 * math.asin(math.sqrt(a))

        if dist_km > 8:
            continue

        # Distance discount: 1.0 at 0km → 0 at 8km
        dist_factor = max(0.0, 1.0 - dist_km / 8.0)

        # Wind alignment: how much the source is upwind of the ward
        wind_factor = 1.0
        if wind_dir is not None:
            # Bearing FROM source TO ward
            dy = ward_lat - src_lat
            dx = (ward_lon - src_lon) * math.cos(math.radians((ward_lat + src_lat) / 2))
            bearing = (math.degrees(math.atan2(dx, dy)) + 360) % 360
            diff = _bearing_diff(bearing, wind_dir)
            wind_factor = max(0.0, 1.0 - diff / 90.0)

        # Source intensity weight
        intensity = {"industrial": 3.0, "vehicular": 1.5, "agricultural": 2.0, "construction": 1.0}.get(src_type, 1.0)
        total_weight += intensity * dist_factor * wind_factor

    # Normalise: cap at 15 AQI offset
    return min(15.0, total_weight * 2.0)


async def run_ward_forecast(db: AsyncSession, city_id: str, ward_id: str) -> ForecastRunOut:
    """Run the hyperlocal forecasting model for a single ward and persist results."""
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    # 1. Ward station centroid (use average of station coords)
    coord_result = await db.execute(
        text("""
            SELECT AVG(ST_Y(geometry::geometry)) AS lat, AVG(ST_X(geometry::geometry)) AS lon
            FROM stations
            WHERE ward_id = :ward_id AND is_active = true AND geometry IS NOT NULL
        """),
        {"ward_id": ward_id},
    )
    coord_row = coord_result.fetchone()
    ward_lat = coord_row[0] if coord_row and coord_row[0] else None
    ward_lon = coord_row[1] if coord_row and coord_row[1] else None

    # 2. City lat/lon for Open-Meteo
    city_result = await db.execute(
        text("SELECT config_json FROM cities WHERE id = :city_id"),
        {"city_id": city_id},
    )
    city_row = city_result.fetchone()
    cfg = city_row[0] if city_row else {}
    city_lat = cfg.get("lat") if cfg else None
    city_lon = cfg.get("lon") if cfg else None

    forecast_lat = ward_lat or city_lat or 28.6139
    forecast_lon = ward_lon or city_lon or 77.2090

    # 3. Open-Meteo 72h forward weather
    om_data = await _fetch_open_meteo(forecast_lat, forecast_lon)
    # Build lookup: ISO hour string → {wind_speed, wind_dir}
    om_lookup: dict[str, dict] = {}
    for entry in om_data:
        t = entry.get("time", "")
        om_lookup[t[:13]] = entry  # key = "YYYY-MM-DDTHH"

    # 4. Ward historical AQI (last 7 days)
    hist_result = await db.execute(
        text("""
            SELECT DATE_TRUNC('hour', sr.ts) AS hour_bucket, ROUND(AVG(sr.aqi))::int AS avg_aqi
            FROM station_readings sr
            JOIN stations s ON s.id = sr.station_id
            WHERE s.ward_id = :ward_id AND s.is_active = true AND sr.aqi IS NOT NULL AND sr.ts >= :since
            GROUP BY hour_bucket ORDER BY hour_bucket
        """),
        {"ward_id": ward_id, "since": now - timedelta(days=7)},
    )
    history = [(row[0], row[1]) for row in hist_result.fetchall()]

    # 5. Diurnal baseline per ward
    hourly_buckets: dict[int, list[int]] = {h: [] for h in range(24)}
    for ts, aqi in history:
        if aqi is not None:
            hourly_buckets[ts.hour].append(aqi)

    all_vals = [v for vals in hourly_buckets.values() for v in vals]
    global_mean = sum(all_vals) / len(all_vals) if all_vals else 200.0
    diurnal_mean: dict[int, float] = {
        h: (sum(vals) / len(vals)) if len(vals) >= 3 else global_mean
        for h, vals in hourly_buckets.items()
    }

    # 6. Ward trend (last 24h)
    last_24h = [(ts, aqi) for ts, aqi in history if ts >= now - timedelta(hours=24)]
    trend_slope = 0.0
    if len(last_24h) >= 4:
        trend_slope = _linear_slope([aqi for _, aqi in last_24h]) * 0.5

    # 7. Emission sources near this ward
    sources_result = await db.execute(
        text("""
            SELECT type, ST_Y(geometry::geometry) AS lat, ST_X(geometry::geometry) AS lon
            FROM emission_sources WHERE city_id = :city_id AND geometry IS NOT NULL
        """),
        {"city_id": city_id},
    )
    sources = [{"type": r[0], "lat": r[1], "lon": r[2]} for r in sources_result.fetchall()]

    # 8. Generate 72 forecast points
    await repo.mark_previous_stale(db, city_id, ward_id=ward_id)

    forecast_rows = []
    for h in range(1, HORIZON_HOURS + 1):
        ts = now + timedelta(hours=h)
        ts_key = ts.strftime("%Y-%m-%dT%H")

        # Per-hour wind from Open-Meteo (fallback: use last available)
        om_entry = om_lookup.get(ts_key)
        hour_wind_speed = om_entry["wind_speed"] if om_entry and om_entry.get("wind_speed") is not None else 3.0
        hour_wind_dir = om_entry["wind_dir"] if om_entry and om_entry.get("wind_dir") is not None else None

        wa = _wind_adj(hour_wind_speed)
        src_offset = _source_proximity_offset(
            ward_lat or forecast_lat,
            ward_lon or forecast_lon,
            sources,
            hour_wind_dir,
        )

        base = diurnal_mean.get(ts.hour, global_mean)
        trend_adj = trend_slope * h
        raw = (base + trend_adj) * wa + src_offset
        predicted_aqi = max(1, min(500, round(raw)))
        predicted_pm25 = _aqi_to_pm25(predicted_aqi)
        confidence = round(max(0.40, 0.92 - 0.007 * (h - 1)), 3)

        forecast_rows.append({
            "city_id": city_id,
            "ward_id": ward_id,
            "generated_at": now,
            "forecast_for_ts": ts,
            "predicted_aqi": predicted_aqi,
            "predicted_pm25": predicted_pm25,
            "confidence": confidence,
            "model_version": MODEL_VERSION,
            "is_stale": False,
        })

    objs = await repo.bulk_insert_forecast(db, forecast_rows)
    points = [ForecastPointOut.model_validate(o) for o in objs]
    peak = max(points, key=lambda p: p.predicted_aqi)

    return ForecastRunOut(
        city_id=city_id,
        ward_id=ward_id,
        generated_at=now,
        model_version=MODEL_VERSION,
        horizon_hours=HORIZON_HOURS,
        points=points,
        peak_aqi=peak.predicted_aqi,
        peak_at=peak.forecast_for_ts,
    )


async def get_latest_ward_forecast(db: AsyncSession, city_id: str, ward_id: str) -> ForecastRunOut | None:
    generated_at, objs = await repo.get_latest_forecast_run(db, city_id, ward_id=ward_id)
    if not objs:
        return None
    points = [ForecastPointOut.model_validate(o) for o in objs]
    peak = max(points, key=lambda p: p.predicted_aqi)
    return ForecastRunOut(
        city_id=city_id,
        ward_id=ward_id,
        generated_at=generated_at,
        model_version=MODEL_VERSION,
        horizon_hours=HORIZON_HOURS,
        points=points,
        peak_aqi=peak.predicted_aqi,
        peak_at=peak.forecast_for_ts,
        is_stale=any(o.is_stale for o in objs),
    )
