"""Attribution Engine — chemical fingerprint + wind dispersion hybrid.

Two-stage algorithm:
Stage 1 — Chemical Fingerprinting (40% weight):
  Identify source types from the pollutant signature of current readings:
  - High NO2 + CO          → Vehicular
  - High SO2 + NO2         → Industrial
  - PM10/PM2.5 ratio > 2.5 → Construction (coarse dust)
  - High PM2.5 + CO, low SO2 → Agricultural/fire burning
  - High O3                → Photochemical (secondary vehicular)
  - Fire hotspots (NASA)   → Fire

Stage 2 — Spatial Dispersion (60% weight):
  For each known emission source: weight = base_type × wind_alignment × distance_decay
  Normalise per source type.

Final score = 0.40 × fingerprint_score + 0.60 × dispersion_score
Confidence = f(data completeness, source count, wind data availability)
"""

import math
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attribution import repository as repo
from app.modules.attribution.schemas import AttributionRankingOut, RankedSource

# Base emission weight by source type (relative importance)
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

# All tracked source types
ALL_SOURCE_TYPES = ["vehicular", "industrial", "construction", "agricultural", "fire", "other"]


# ── Math helpers ──────────────────────────────────────────────────────────────


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _wind_alignment(source_bearing: float, wind_dir: float | None) -> float:
    if wind_dir is None:
        return 0.5
    angle_diff = abs(source_bearing - wind_dir) % 360
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    return (math.cos(math.radians(angle_diff)) + 1) / 2


def _distance_decay(distance_km: float) -> float:
    return 1.0 / max(distance_km**2, 0.01)


def _wind_description(wind_dir: float | None, wind_speed: float | None) -> str | None:
    if wind_dir is None:
        return None
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(wind_dir / 45) % 8
    speed_str = f"{wind_speed:.1f} m/s" if wind_speed is not None else "unknown speed"
    return f"Wind from {directions[idx]} at {speed_str}"


# ── Stage 1: Chemical fingerprinting ─────────────────────────────────────────


def _vehicular_multiplier(
    congestion_ratio: float | None, hour_utc: int, city_tz_offset: float = 5.5
) -> float:
    """Derive vehicular activity multiplier from real TomTom congestion data.

    congestion_ratio = free_flow_speed / current_speed (TomTom definition):
      1.0 → free flow (no traffic)   → multiplier ~0.4
      1.5 → moderate congestion      → multiplier ~0.7
      2.0+ → heavy congestion        → multiplier ~1.4

    Falls back to time-of-day estimate when TomTom data is unavailable.
    """
    if congestion_ratio is not None:
        # Linear scale: ratio 1.0→2.5 maps to multiplier 0.4→1.4
        return round(0.4 + min(max(congestion_ratio - 1.0, 0.0), 1.5) / 1.5 * 1.0, 3)
    # Fallback: estimate from local hour
    local_hour = (hour_utc + city_tz_offset) % 24
    if 7 <= local_hour < 10 or 17 <= local_hour < 21:
        return 1.4
    elif 10 <= local_hour < 17:
        return 0.9
    elif 21 <= local_hour or local_hour < 6:
        return 0.4
    return 0.7


def _non_vehicular_factors(hour_utc: int, city_tz_offset: float = 5.5) -> dict[str, float]:
    """Time-of-day multipliers for sources that have no real-time sensor proxy."""
    local_hour = (hour_utc + city_tz_offset) % 24
    if 7 <= local_hour < 10 or 17 <= local_hour < 21:
        return {"industrial": 1.0, "agricultural": 0.6, "construction": 1.1}
    elif 10 <= local_hour < 17:
        return {"industrial": 1.0, "agricultural": 0.8, "construction": 1.2}
    elif 21 <= local_hour or local_hour < 6:
        return {"industrial": 1.3, "agricultural": 1.4, "construction": 0.3}
    return {"industrial": 1.1, "agricultural": 1.1, "construction": 0.6}


def _chemical_fingerprint(
    pm25: float | None,
    pm10: float | None,
    no2: float | None,
    so2: float | None,
    co: float | None,
    o3: float | None,
    fire_count: int = 0,
    hour_utc: int | None = None,
    congestion_ratio: float | None = None,
) -> dict[str, float]:
    """
    Return unnormalised scores per source type based on pollutant signature.

    Vehicular weight driven by real TomTom congestion_ratio when available.
    Industrial/agricultural/construction weighted by time-of-day (no real-time proxy).

    Thresholds based on CPCB/WHO reference ranges for Indian urban air:
      NO2 > 80 µg/m³            → heavy vehicular / industrial combustion
      SO2 > 20 µg/m³            → industrial (coal/oil burning)
      CO  > 10 mg/m³            → industrial furnaces / heavy burning
      CO  3–10 mg/m³            → combustion (vehicular or burning)
      O3  > 50 µg/m³            → photochemical smog (secondary vehicular)
      PM10/PM2.5 ratio > 2.5    → construction / road dust
      PM10 < PM2.5              → sensor cross-contamination, skip ratio
      PM2.5 > 60 + CO > 2 + low SO2 → biomass burning
    """
    scores: dict[str, float] = {t: 0.0 for t in ALL_SOURCE_TYPES}
    data_points = 0

    cur_hour = hour_utc if hour_utc is not None else datetime.now(UTC).hour
    v_mul = _vehicular_multiplier(congestion_ratio, cur_hour)
    nv = _non_vehicular_factors(cur_hour)

    # --- Vehicular signature: NO2 + CO ---
    if no2 is not None:
        data_points += 1
        if no2 > 80:
            scores["vehicular"] += 2.0 * v_mul
        elif no2 > 40:
            scores["vehicular"] += 1.0 * v_mul
        elif no2 > 20:
            scores["vehicular"] += 0.4 * v_mul

    if co is not None:
        data_points += 1
        if co > 10.0:
            # Very high CO = industrial furnace / heavy burning, not road traffic
            scores["industrial"] += 1.5 * nv["industrial"]
            scores["agricultural"] += 0.8 * nv["agricultural"]
        elif co > 3.0:
            scores["vehicular"] += 1.5 * v_mul
            scores["agricultural"] += 0.5 * nv["agricultural"]
            # When traffic is light (TomTom shows free flow) but CO is still elevated,
            # the combustion is coming from non-vehicular sources
            if v_mul < 0.6:
                scores["industrial"] += 0.8 * nv["industrial"]
        elif co > 1.5:
            scores["vehicular"] += 0.8 * v_mul
        elif co > 0.8:
            scores["vehicular"] += 0.3 * v_mul

    # --- Industrial signature: SO2 (+ NO2 combo) ---
    if so2 is not None:
        data_points += 1
        if so2 > 40:
            scores["industrial"] += 2.5 * nv["industrial"]
        elif so2 > 20:
            scores["industrial"] += 1.5 * nv["industrial"]
            scores["vehicular"] += 0.3 * v_mul  # diesel overlap
        elif so2 > 8:
            scores["industrial"] += 0.6 * nv["industrial"]

    if so2 is not None and no2 is not None and so2 > 15 and no2 > 40:
        scores["industrial"] += 1.0 * nv["industrial"]

    # --- Construction signature: coarse PM ratio ---
    # Guard: PM10 < PM2.5 is physically impossible — cross-station averaging artifact, skip
    pm_ratio_valid = pm25 is not None and pm10 is not None and pm25 > 0 and pm10 >= pm25
    if pm_ratio_valid:
        data_points += 1
        ratio = pm10 / pm25  # type: ignore[operator]
        if ratio > 3.0:
            scores["construction"] += 2.0 * nv["construction"]
        elif ratio > 2.5:
            scores["construction"] += 1.2 * nv["construction"]
        elif ratio > 2.0:
            scores["construction"] += 0.5 * nv["construction"]
        if ratio < 1.5 and pm25 > 60:
            scores["vehicular"] += 0.4 * v_mul
            scores["agricultural"] += 0.4 * nv["agricultural"]

    # --- Agricultural / biomass burning: PM2.5 high + CO present + low SO2 ---
    # Skip when PM10 < PM2.5 (cross-station averaging artifact — PM2.5 value untrustworthy)
    # Also require CO > 2 to distinguish from plain dust/industrial PM
    pm25_reliable = pm25 is not None and (pm10 is None or pm10 >= pm25)
    if pm25_reliable and pm25 > 60 and co is not None and co > 2.0:  # type: ignore[operator]
        data_points += 1
        base_agri = (pm25 - 60) / 100  # type: ignore[operator]
        if so2 is None or so2 < 15:
            scores["agricultural"] += min(base_agri * 1.5, 1.5) * nv["agricultural"]
        if co > 1.5:
            scores["agricultural"] += 0.8 * nv["agricultural"]
    elif pm25 is not None and pm25 > 60:
        data_points += 1  # count PM2.5 data point even when agricultural rule doesn't fire

    # --- Fire signature: NASA hotspots ---
    if fire_count > 0:
        scores["fire"] += min(fire_count * 0.8, 3.0)
        scores["agricultural"] += min(fire_count * 0.3, 1.0)

    # --- Photochemical / O3: secondary vehicular (forms in sunlight) ---
    if o3 is not None:
        data_points += 1
        if o3 > 80:
            scores["vehicular"] += 1.0 * v_mul
        elif o3 > 50:
            scores["vehicular"] += 0.5 * v_mul

    if data_points == 0:
        return {
            "vehicular": 0.40,
            "industrial": 0.25,
            "construction": 0.15,
            "agricultural": 0.12,
            "fire": 0.0,
            "other": 0.08,
        }

    return scores


# ── Stage 2: Spatial dispersion ───────────────────────────────────────────────


def _dispersion_scores(
    sources: list,
    fire_hotspots: list,
    receptor_lat: float,
    receptor_lon: float,
    wind_dir: float | None,
) -> dict[str, float]:
    """Compute per-source-type dispersion weight from emission sources + fire hotspots."""
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

    for fh in fire_hotspots:
        fh_lat, fh_lon = float(fh[1]), float(fh[2])
        dist = _haversine_km(receptor_lat, receptor_lon, fh_lat, fh_lon)
        bearing = _bearing(receptor_lat, receptor_lon, fh_lat, fh_lon)
        alignment = _wind_alignment(bearing, wind_dir)
        decay = _distance_decay(max(dist, 0.1))
        weight = _BASE_WEIGHTS["fire"] * alignment * decay
        type_weights["fire"] = type_weights.get("fire", 0.0) + weight

    if not type_weights:
        type_weights = {
            "vehicular": 0.40,
            "industrial": 0.25,
            "construction": 0.15,
            "agricultural": 0.12,
            "other": 0.08,
        }

    return type_weights


# ── Hybrid combiner ───────────────────────────────────────────────────────────

FINGERPRINT_WEIGHT = 0.40
DISPERSION_WEIGHT = 0.60


def _combine_scores(
    fingerprint: dict[str, float],
    dispersion: dict[str, float],
) -> dict[str, float]:
    """Normalise each stage to [0,1] then blend with fixed weights."""

    def _normalise(d: dict[str, float]) -> dict[str, float]:
        total = sum(d.values()) or 1.0
        return {k: v / total for k, v in d.items()}

    fp_norm = _normalise(fingerprint)
    dp_norm = _normalise(dispersion)

    all_types = set(fp_norm) | set(dp_norm)
    combined = {
        t: FINGERPRINT_WEIGHT * fp_norm.get(t, 0.0) + DISPERSION_WEIGHT * dp_norm.get(t, 0.0)
        for t in all_types
    }
    total = sum(combined.values()) or 1.0
    return {k: round(v / total * 100, 2) for k, v in combined.items()}


def _confidence_score(
    data_points: int,
    source_count: int,
    has_wind: bool,
    fire_count: int,
) -> float:
    """
    0–1 confidence score:
    - Full pollutant data + sources + wind → ~0.85
    - Only PM data, no wind → ~0.45
    """
    score = 0.0
    score += min(data_points / 6.0, 1.0) * 0.40  # pollutant completeness
    score += min(source_count / 4.0, 1.0) * 0.30  # spatial source coverage
    score += 0.20 if has_wind else 0.0  # wind data
    score += min(fire_count / 2.0, 1.0) * 0.10  # fire data quality
    return round(min(score, 1.0), 3)


# ── City centroid helper ───────────────────────────────────────────────────────


async def _get_city_centroid(db: AsyncSession, city_id: str) -> tuple[float, float] | None:
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


# ── Main compute function ─────────────────────────────────────────────────────


async def compute_attribution(db: AsyncSession, city_id: str) -> AttributionRankingOut:
    """Run hybrid attribution (chemical fingerprint + wind dispersion) and persist."""
    now = datetime.now(UTC)

    # 1. Pollutant readings from the single worst-AQI station (CPCB representative station).
    #    Using the max-AQI station ensures PM2.5 and PM10 are always from the same source,
    #    so PM10 >= PM2.5 is guaranteed (no cross-station averaging artifact).
    #    Gas pollutants (NO2, SO2, CO, O3) are averaged across all valid stations because
    #    they disperse more uniformly and more stations = better signal.
    pollutant_result = await db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (sr.station_id)
                    sr.aqi, sr.pm25, sr.pm10, sr.no2, sr.so2, sr.co, sr.o3
                FROM station_readings sr
                JOIN stations s ON s.id = sr.station_id
                WHERE s.city_id = :city_id AND s.is_active = true
                  AND sr.aqi BETWEEN 0 AND 500
                  AND (sr.pm25 IS NULL OR sr.pm25 <= 900)
                  AND sr.ts >= NOW() - INTERVAL '24 hours'
                ORDER BY sr.station_id, sr.ts DESC
            ),
            worst_station AS (
                SELECT pm25, pm10, aqi
                FROM latest
                ORDER BY aqi DESC NULLS LAST
                LIMIT 1
            )
            SELECT
                (SELECT ROUND(aqi)::int FROM worst_station)  AS avg_aqi,
                (SELECT pm25 FROM worst_station)             AS avg_pm25,
                (SELECT pm10 FROM worst_station)             AS avg_pm10,
                AVG(no2)                                     AS avg_no2,
                AVG(so2)                                     AS avg_so2,
                AVG(co)                                      AS avg_co,
                AVG(o3)                                      AS avg_o3
            FROM latest
            """
        ),
        {"city_id": city_id},
    )
    p = pollutant_result.fetchone()
    current_aqi: int | None = p[0] if p else None
    avg_pm25 = float(p[1]) if p and p[1] is not None else None
    avg_pm10 = float(p[2]) if p and p[2] is not None else None
    avg_no2 = float(p[3]) if p and p[3] is not None else None
    avg_so2 = float(p[4]) if p and p[4] is not None else None
    avg_co = float(p[5]) if p and p[5] is not None else None
    avg_o3 = float(p[6]) if p and p[6] is not None else None

    # Count how many pollutants have valid readings
    data_points = sum(
        1 for v in [avg_pm25, avg_pm10, avg_no2, avg_so2, avg_co, avg_o3] if v is not None
    )

    # 2. Latest weather reading
    weather_result = await db.execute(
        text(
            """
            SELECT wind_speed, wind_dir FROM weather_readings
            WHERE city_id = :city_id ORDER BY ts DESC LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    wr = weather_result.fetchone()
    wind_speed: float | None = float(wr[0]) if wr and wr[0] is not None else None
    wind_dir: float | None = float(wr[1]) if wr and wr[1] is not None else None

    # 3. City receptor centroid
    centroid = await _get_city_centroid(db, city_id)
    if centroid is None:
        centroid = (28.6139, 77.2090)
    receptor_lat, receptor_lon = centroid

    # 4. Known emission sources
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

    # 5. Active fire hotspots (last 24h)
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

    # 5b. Traffic congestion boost — query avg congestion ratio from latest poll
    from app.modules.ingestion.repository import get_avg_congestion_ratio

    avg_congestion = await get_avg_congestion_ratio(db, city_id)

    # 6. Stage 1 — Chemical fingerprint
    # Vehicular weight driven by real TomTom congestion_ratio; other sources by time-of-day
    fp_scores = _chemical_fingerprint(
        pm25=avg_pm25,
        pm10=avg_pm10,
        no2=avg_no2,
        so2=avg_so2,
        co=avg_co,
        o3=avg_o3,
        fire_count=len(fire_hotspots),
        hour_utc=now.hour,
        congestion_ratio=avg_congestion,
    )

    # 7. Stage 2 — Spatial dispersion
    dp_scores = _dispersion_scores(
        sources=sources,
        fire_hotspots=fire_hotspots,
        receptor_lat=receptor_lat,
        receptor_lon=receptor_lon,
        wind_dir=wind_dir,
    )

    # 8. Hybrid blend
    breakdown = _combine_scores(fp_scores, dp_scores)
    dominant = max(breakdown, key=breakdown.get)  # type: ignore[arg-type]

    # 9. Confidence score
    confidence = _confidence_score(
        data_points=data_points,
        source_count=len(sources),
        has_wind=wind_dir is not None,
        fire_count=len(fire_hotspots),
    )

    # 10. Build notes string for transparency
    notes_parts = []
    if avg_pm25 is not None:
        notes_parts.append(f"PM25={avg_pm25:.1f}")
    if avg_pm10 is not None:
        notes_parts.append(f"PM10={avg_pm10:.1f}")
    if avg_no2 is not None:
        notes_parts.append(f"NO2={avg_no2:.1f}")
    if avg_so2 is not None:
        notes_parts.append(f"SO2={avg_so2:.1f}")
    if avg_co is not None:
        notes_parts.append(f"CO={avg_co:.2f}")
    if avg_o3 is not None:
        notes_parts.append(f"O3={avg_o3:.1f}")
    notes_parts.append(f"confidence={confidence:.2f}")
    if avg_congestion is not None:
        notes_parts.append(f"congestion={avg_congestion:.2f}")
    notes = " | ".join(notes_parts)

    # 11. Persist
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
        "notes": notes,
    }
    await repo.create_attribution(db, attr_data)

    # 12. Evaluate alert thresholds
    if current_aqi is not None:
        await _evaluate_alerts(db, city_id, current_aqi, dominant, now)

    # 13. Build response
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
        confidence_score=confidence,
        pollutant_snapshot={
            "pm25": avg_pm25,
            "pm10": avg_pm10,
            "no2": avg_no2,
            "so2": avg_so2,
            "co": avg_co,
            "o3": avg_o3,
        },
    )


async def _evaluate_alerts(
    db: AsyncSession,
    city_id: str,
    aqi: int,
    dominant_source: str | None,
    now: datetime,
) -> None:
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

    # Parse confidence and pollutant snapshot from notes field
    confidence = None
    pollutant_snapshot = None
    if attr.notes:
        try:
            parts = dict(item.split("=") for item in attr.notes.split(" | ") if "=" in item)
            confidence = float(parts.get("confidence", 0)) if "confidence" in parts else None
            pollutant_snapshot = {
                "pm25": float(parts["PM25"]) if "PM25" in parts else None,
                "pm10": float(parts["PM10"]) if "PM10" in parts else None,
                "no2": float(parts["NO2"]) if "NO2" in parts else None,
                "so2": float(parts["SO2"]) if "SO2" in parts else None,
                "co": float(parts["CO"]) if "CO" in parts else None,
                "o3": float(parts["O3"]) if "O3" in parts else None,
            }
        except Exception:
            pass

    return AttributionRankingOut(
        city_id=attr.city_id,
        computed_at=attr.computed_at,
        aqi=attr.aqi_at_computation,
        dominant_source=attr.dominant_source,
        ranked_sources=ranked,
        wind_speed=attr.wind_speed,
        wind_dir=attr.wind_dir,
        wind_description=_wind_description(attr.wind_dir, attr.wind_speed),
        confidence_score=confidence,
        pollutant_snapshot=pollutant_snapshot,
    )
