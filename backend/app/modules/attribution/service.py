"""Attribution Engine — computes source contributions to current AQI.

Algorithm (simplified physics-based dispersion):
1. Pull latest city AQI from station_readings (average of active stations).
2. Pull latest weather reading for the city to get wind_speed + wind_dir.
3. For each emission_source in the city, compute a dispersion weight:
     weight = base_type_weight(source.type)
              * distance_decay(distance_km)
              * wind_alignment(source_bearing, wind_dir)
4. Normalise weights → percentages.
5. Identify dominant_source (highest pct).
6. Persist to attributions table.
7. Evaluate alert thresholds (200/300/400) and create/resolve aqi_alerts.
"""

import math
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attribution import repository as repo
from app.modules.attribution.schemas import AttributionRankingOut, RankedSource

# Base emission weight by source type (relative importance, before distance/wind)
_BASE_WEIGHTS: dict[str, float] = {
    "vehicular": 1.0,
    "industrial": 1.3,
    "construction": 0.7,
    "agricultural": 0.9,
    "fire": 1.5,
    "other": 0.5,
}

# Alert thresholds: (threshold, level_label)
ALERT_THRESHOLDS = [
    (400, "severe"),
    (300, "very_poor"),
    (200, "poor"),
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) pairs."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Bearing in degrees (0=N, 90=E, 180=S, 270=W) from point 1 → point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _wind_alignment(source_bearing: float, wind_dir: float | None) -> float:
    """
    Return [0,1] alignment factor.

    wind_dir is the direction FROM which the wind blows (met convention).
    A source upwind (directly behind the station relative to wind) gets factor ~1.
    A source downwind (ahead of the station) gets factor ~0.
    """
    if wind_dir is None:
        return 0.5  # no wind data — neutral
    # Wind blows FROM wind_dir, so upwind direction is wind_dir itself
    angle_diff = abs(source_bearing - wind_dir) % 360
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    # cosine similarity mapped to [0,1]: 0° diff → 1.0, 180° → 0.0
    return (math.cos(math.radians(angle_diff)) + 1) / 2


def _distance_decay(distance_km: float) -> float:
    """Inverse-square decay with a floor at 0.1 to avoid division by zero."""
    return 1.0 / max(distance_km**2, 0.01)


def _wind_description(wind_dir: float | None, wind_speed: float | None) -> str | None:
    if wind_dir is None:
        return None
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(wind_dir / 45) % 8
    speed_str = f"{wind_speed:.1f} m/s" if wind_speed is not None else "unknown speed"
    return f"Wind from {directions[idx]} at {speed_str}"


async def _get_city_centroid(db: AsyncSession, city_id: str) -> tuple[float, float] | None:
    """Return (lat, lon) centroid from the city's stations, or None."""
    result = await db.execute(
        text(
            """
            SELECT AVG(ST_Y(geometry::geometry)), AVG(ST_X(geometry::geometry))
            FROM stations
            WHERE city_id = :city_id AND is_active = true
            """
        ),
        {"city_id": city_id},
    )
    row = result.fetchone()
    if row and row[0] is not None:
        return float(row[0]), float(row[1])
    return None


async def compute_attribution(db: AsyncSession, city_id: str) -> AttributionRankingOut:
    """Run the attribution computation and persist the result."""
    now = datetime.now(UTC)

    # 1. Current city AQI (average of latest readings per active station)
    aqi_result = await db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (sr.station_id)
                    sr.aqi
                FROM station_readings sr
                JOIN stations s ON s.id = sr.station_id
                WHERE s.city_id = :city_id AND s.is_active = true AND sr.aqi IS NOT NULL
                ORDER BY sr.station_id, sr.ts DESC
            )
            SELECT ROUND(AVG(aqi))::int FROM latest
            """
        ),
        {"city_id": city_id},
    )
    aqi_row = aqi_result.fetchone()
    current_aqi: int | None = aqi_row[0] if aqi_row else None

    # 2. Latest weather reading
    weather_result = await db.execute(
        text(
            """
            SELECT wind_speed, wind_dir
            FROM weather_readings
            WHERE city_id = :city_id
            ORDER BY ts DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    weather_row = weather_result.fetchone()
    wind_speed: float | None = (
        float(weather_row[0]) if weather_row and weather_row[0] is not None else None
    )
    wind_dir: float | None = (
        float(weather_row[1]) if weather_row and weather_row[1] is not None else None
    )

    # 3. City centroid (average station location) used as the "receptor point"
    centroid = await _get_city_centroid(db, city_id)
    if centroid is None:
        centroid = (28.6139, 77.2090)  # Delhi fallback

    receptor_lat, receptor_lon = centroid

    # 4. Emission sources for the city
    sources_result = await db.execute(
        text(
            """
            SELECT id, type,
                   ST_Y(geometry::geometry) AS lat,
                   ST_X(geometry::geometry) AS lon
            FROM emission_sources
            WHERE city_id = :city_id AND geometry IS NOT NULL
            """
        ),
        {"city_id": city_id},
    )
    sources = sources_result.fetchall()

    # Also account for fire hotspots in last 24h
    fire_result = await db.execute(
        text(
            """
            SELECT id,
                   ST_Y(geometry::geometry) AS lat,
                   ST_X(geometry::geometry) AS lon
            FROM fire_hotspots
            WHERE city_id = :city_id
              AND detected_at > NOW() - INTERVAL '24 hours'
              AND geometry IS NOT NULL
            """
        ),
        {"city_id": city_id},
    )
    fire_hotspots = fire_result.fetchall()

    # Build weighted contributions per source type
    type_weights: dict[str, float] = {}

    for src in sources:
        src_type = src[1] or "other"
        src_lat, src_lon = float(src[2]), float(src[3])
        dist = _haversine_km(receptor_lat, receptor_lon, src_lat, src_lon)
        bearing = _bearing(receptor_lat, receptor_lon, src_lat, src_lon)
        base = _BASE_WEIGHTS.get(src_type, 0.5)
        alignment = _wind_alignment(bearing, wind_dir)
        decay = _distance_decay(max(dist, 0.1))
        weight = base * alignment * decay
        type_weights[src_type] = type_weights.get(src_type, 0.0) + weight

    for _ in fire_hotspots:
        type_weights["fire"] = type_weights.get("fire", 0.0) + _BASE_WEIGHTS["fire"]

    # If no sources found, fall back to a Delhi-typical split
    if not type_weights:
        type_weights = {
            "vehicular": 0.40,
            "industrial": 0.25,
            "construction": 0.15,
            "agricultural": 0.12,
            "other": 0.08,
        }

    total = sum(type_weights.values()) or 1.0
    breakdown = {k: round(v / total * 100, 2) for k, v in type_weights.items()}
    dominant = max(breakdown, key=breakdown.get)  # type: ignore[arg-type]

    # 5. Persist attribution
    attr_data = {
        "city_id": city_id,
        "computed_at": now,
        "aqi_at_computation": current_aqi,
        "dominant_source": dominant,
        "vehicular_pct": breakdown.get("vehicular"),
        "industrial_pct": breakdown.get("industrial"),
        "construction_pct": breakdown.get("construction"),
        "agricultural_pct": breakdown.get("agricultural"),
        "fire_pct": breakdown.get("fire"),
        "other_pct": breakdown.get("other"),
        "wind_speed": wind_speed,
        "wind_dir": wind_dir,
        "source_count": len(sources) + len(fire_hotspots),
        "notes": None,
    }
    await repo.create_attribution(db, attr_data)

    # 6. Evaluate alert thresholds
    if current_aqi is not None:
        await _evaluate_alerts(db, city_id, current_aqi, dominant, now)

    # 7. Build response
    ranked = sorted(
        [RankedSource(source_type=k, contribution_pct=v, rank=0) for k, v in breakdown.items()],
        key=lambda x: x.contribution_pct,
        reverse=True,
    )
    for i, r in enumerate(ranked):
        r.rank = i + 1

    return AttributionRankingOut(
        city_id=city_id,
        computed_at=now,
        aqi=current_aqi,
        dominant_source=dominant,
        ranked_sources=ranked,
        wind_speed=wind_speed,
        wind_dir=wind_dir,
        wind_description=_wind_description(wind_dir, wind_speed),
    )


async def _evaluate_alerts(
    db: AsyncSession,
    city_id: str,
    aqi: int,
    dominant_source: str | None,
    now: datetime,
) -> None:
    """Create new alerts when threshold is crossed; resolve them when AQI drops below."""
    for threshold, level in ALERT_THRESHOLDS:
        existing = await repo.get_active_alert_for_threshold(db, city_id, threshold)
        if aqi >= threshold:
            if existing is None:
                await repo.create_alert(
                    db,
                    {
                        "city_id": city_id,
                        "alert_level": level,
                        "threshold": threshold,
                        "aqi_value": aqi,
                        "dominant_source": dominant_source,
                        "triggered_at": now,
                        "is_active": True,
                    },
                )
        else:
            if existing is not None:
                await repo.resolve_alert(db, existing, now)


async def get_latest_attribution_ranking(
    db: AsyncSession, city_id: str
) -> AttributionRankingOut | None:
    attr = await repo.get_latest_attribution(db, city_id)
    if attr is None:
        return None
    breakdown = {
        "vehicular": attr.vehicular_pct or 0,
        "industrial": attr.industrial_pct or 0,
        "construction": attr.construction_pct or 0,
        "agricultural": attr.agricultural_pct or 0,
        "fire": attr.fire_pct or 0,
        "other": attr.other_pct or 0,
    }
    ranked = sorted(
        [
            RankedSource(source_type=k, contribution_pct=v, rank=0)
            for k, v in breakdown.items()
            if v > 0
        ],
        key=lambda x: x.contribution_pct,
        reverse=True,
    )
    for i, r in enumerate(ranked):
        r.rank = i + 1
    return AttributionRankingOut(
        city_id=attr.city_id,
        computed_at=attr.computed_at,
        aqi=attr.aqi_at_computation,
        dominant_source=attr.dominant_source,
        ranked_sources=ranked,
        wind_speed=attr.wind_speed,
        wind_dir=attr.wind_dir,
        wind_description=_wind_description(attr.wind_dir, attr.wind_speed),
    )
