"""Forecasting Engine — 72-hour AQI prediction for a city.

Model: Diurnal Pattern + Recent Trend + Wind Adjustment (no external ML deps)

Algorithm:
1. Pull last 7 days of hourly city-average AQI from station_readings.
2. Compute mean AQI per hour-of-day (0-23) → diurnal baseline.
3. Compute recent linear trend from last 24h of hourly averages.
4. Pull latest weather reading → wind_speed → dispersion adjustment.
5. For each of 72 future hours:
     base      = diurnal_mean[hour_of_day]  (or global mean if <3 readings for that hour)
     trend_adj = slope × hours_ahead  (slope dampened by 0.7 to avoid runaway extrapolation)
     wind_adj  = 1.0 - 0.04 × wind_speed  (capped to [0.5, 1.3])
     predicted = max(1, round(base + trend_adj) × wind_adj)
6. Derive predicted_pm25 from predicted_aqi via inverse AQI breakpoints.
7. Confidence decreases with forecast horizon (1.0 → 0.5 over 72h).
8. Persist 72 rows; mark previous batch stale.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forecasting import repository as repo
from app.modules.forecasting.schemas import ForecastPointOut, ForecastRunOut

MODEL_VERSION = "diurnal-v1"
HORIZON_HOURS = 72


def _aqi_to_pm25(aqi: int) -> float:
    """Inverse AQI breakpoint lookup — returns approximate PM2.5 (µg/m³)."""
    breakpoints = [
        (0, 50, 0.0, 30.0),
        (51, 100, 30.0, 60.0),
        (101, 200, 60.0, 90.0),
        (201, 300, 90.0, 120.0),
        (301, 400, 120.0, 250.0),
        (401, 500, 250.0, 500.0),
    ]
    aqi = max(0, min(500, aqi))
    for i_lo, i_hi, c_lo, c_hi in breakpoints:
        if i_lo <= aqi <= i_hi:
            return round(c_lo + (c_hi - c_lo) * (aqi - i_lo) / (i_hi - i_lo), 2)
    return 500.0


def _linear_slope(values: list[float]) -> float:
    """Least-squares slope over a sequence of evenly-spaced values."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


async def run_forecast(db: AsyncSession, city_id: str) -> ForecastRunOut:
    """Run the forecasting model and persist results."""
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    # 1. Pull last 7 days of hourly city-average AQI
    rows_result = await db.execute(
        text(
            """
            SELECT
                DATE_TRUNC('hour', sr.ts) AS hour_bucket,
                ROUND(AVG(sr.aqi))::int   AS avg_aqi
            FROM station_readings sr
            JOIN stations s ON s.id = sr.station_id
            WHERE s.city_id = :city_id
              AND s.is_active = true
              AND sr.aqi IS NOT NULL
              AND sr.ts >= :since
            GROUP BY hour_bucket
            ORDER BY hour_bucket
            """
        ),
        {"city_id": city_id, "since": now - timedelta(days=7)},
    )
    history = [(row[0], row[1]) for row in rows_result.fetchall()]

    # 2. Compute diurnal baseline (mean AQI per hour of day)
    hourly_buckets: dict[int, list[int]] = {h: [] for h in range(24)}
    for ts, aqi in history:
        if aqi is not None:
            hourly_buckets[ts.hour].append(aqi)

    global_mean = sum(v for vals in hourly_buckets.values() for v in vals) / max(
        1, sum(len(v) for v in hourly_buckets.values())
    )
    diurnal_mean: dict[int, float] = {
        h: (sum(vals) / len(vals)) if len(vals) >= 3 else global_mean
        for h, vals in hourly_buckets.items()
    }

    # 3. Recent trend (last 24h of hourly averages)
    last_24h = [(ts, aqi) for ts, aqi in history if ts >= now - timedelta(hours=24)]
    trend_slope = 0.0
    if len(last_24h) >= 4:
        trend_slope = _linear_slope([aqi for _, aqi in last_24h])
    # Dampen slope to avoid long-horizon runaway
    trend_slope *= 0.5

    # 4. Wind adjustment
    weather_result = await db.execute(
        text(
            "SELECT wind_speed FROM weather_readings "
            "WHERE city_id = :city_id ORDER BY ts DESC LIMIT 1"
        ),
        {"city_id": city_id},
    )
    weather_row = weather_result.fetchone()
    wind_speed = float(weather_row[0]) if weather_row and weather_row[0] is not None else 3.0
    wind_adj = max(0.5, min(1.3, 1.0 - 0.04 * wind_speed))

    # 5. Generate 72 forecast points
    await repo.mark_previous_stale(db, city_id)

    forecast_rows = []
    for h in range(1, HORIZON_HOURS + 1):
        ts = now + timedelta(hours=h)
        base = diurnal_mean.get(ts.hour, global_mean)
        trend_adj = trend_slope * h
        raw = (base + trend_adj) * wind_adj
        predicted_aqi = max(1, min(500, round(raw)))
        predicted_pm25 = _aqi_to_pm25(predicted_aqi)
        # Confidence degrades with horizon: 0.95 at h=1, ~0.55 at h=72
        confidence = round(max(0.50, 0.95 - 0.006 * (h - 1)), 3)
        forecast_rows.append(
            {
                "city_id": city_id,
                "generated_at": now,
                "forecast_for_ts": ts,
                "predicted_aqi": predicted_aqi,
                "predicted_pm25": predicted_pm25,
                "confidence": confidence,
                "model_version": MODEL_VERSION,
                "is_stale": False,
            }
        )

    objs = await repo.bulk_insert_forecast(db, forecast_rows)
    points = [ForecastPointOut.model_validate(o) for o in objs]

    peak = max(points, key=lambda p: p.predicted_aqi)

    return ForecastRunOut(
        city_id=city_id,
        generated_at=now,
        model_version=MODEL_VERSION,
        horizon_hours=HORIZON_HOURS,
        points=points,
        peak_aqi=peak.predicted_aqi,
        peak_at=peak.forecast_for_ts,
    )


async def get_latest_forecast(db: AsyncSession, city_id: str) -> ForecastRunOut | None:
    """Return the most recently generated forecast without recomputing."""
    generated_at, objs = await repo.get_latest_forecast_run(db, city_id)
    if not objs:
        return None
    points = [ForecastPointOut.model_validate(o) for o in objs]
    peak = max(points, key=lambda p: p.predicted_aqi)
    return ForecastRunOut(
        city_id=city_id,
        generated_at=generated_at,
        model_version=MODEL_VERSION,
        horizon_hours=HORIZON_HOURS,
        points=points,
        peak_aqi=peak.predicted_aqi,
        peak_at=peak.forecast_for_ts,
        is_stale=any(o.is_stale for o in objs),
    )
