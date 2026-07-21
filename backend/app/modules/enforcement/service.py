"""Enforcement Agent — priority scoring and evidence brief generation.

Scoring formula:
    priority_score = 0.35 × source_attribution  (60% category pct + 40% spatial proximity)
                   + 0.30 × forecast_severity
                   + 0.20 × permit_status
                   + 0.15 × days_since_inspection

Spatial proximity: haversine distance from source to worst-AQI ward centroid,
weighted by wind alignment (upwind sources score higher).
"""

import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_client import generate_text
from app.modules.enforcement import repository as repo
from app.modules.enforcement.schemas import (
    EmissionSourceBrief,
    EnforcementItemOut,
    EnforcementListOut,
)

_PERMIT_WEIGHT = {"expired": 1.0, "pending": 0.6, "active": 0.2}
_MAX_DAYS_SINCE_INSPECTION = 30


def _permit_score(permit_status: str) -> float:
    return _PERMIT_WEIGHT.get(permit_status, 0.5)


def _days_since_score(last_inspected_at: datetime | None) -> float:
    if last_inspected_at is None:
        return 1.0
    now = datetime.now(UTC)
    days = (now - last_inspected_at).days
    return min(days / _MAX_DAYS_SINCE_INSPECTION, 1.0)


def _forecast_severity(peak_aqi_24h: float) -> float:
    return min(peak_aqi_24h / 500.0, 1.0)


def _attribution_weight(source_type: str, breakdown: dict) -> float:
    key = f"{source_type}_pct"
    pct = breakdown.get(key) or 0.0
    return min(pct / 100.0, 1.0)


def _spatial_proximity_score(
    src_lat: float | None,
    src_lon: float | None,
    ward_lat: float | None,
    ward_lon: float | None,
    wind_dir: float | None,
    max_km: float = 15.0,
) -> float:
    """Score [0, 1] — how directly upwind and close a source is to the worst ward.

    Distance factor: 1.0 at 0 km, 0 at max_km.
    Wind alignment: 1.0 when source is directly upwind (bearing from source to ward
    matches wind direction), 0 when perpendicular or downwind.
    Returns 0.5 (neutral) when coordinates are unavailable.
    """
    if src_lat is None or src_lon is None or ward_lat is None or ward_lon is None:
        return 0.5

    dlat = math.radians(ward_lat - src_lat)
    dlon = math.radians(ward_lon - src_lon)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(src_lat))
        * math.cos(math.radians(ward_lat))
        * math.sin(dlon / 2) ** 2
    )
    dist_km = 6371 * 2 * math.asin(math.sqrt(max(0.0, a)))

    if dist_km > max_km:
        return 0.0

    dist_factor = 1.0 - dist_km / max_km

    if wind_dir is None:
        return dist_factor * 0.7  # no wind info — partial credit

    # Bearing FROM source TO ward
    dy = ward_lat - src_lat
    dx = (ward_lon - src_lon) * math.cos(math.radians((src_lat + ward_lat) / 2))
    bearing = (math.degrees(math.atan2(dx, dy)) + 360) % 360

    # Angular difference between bearing and wind direction
    diff = abs(bearing - wind_dir) % 360
    diff = min(diff, 360 - diff)
    wind_factor = max(0.0, 1.0 - diff / 90.0)  # 1.0 at 0°, 0 at 90°+

    return dist_factor * wind_factor


def _build_evidence_brief_template(
    source_name: str,
    source_type: str,
    permit_status: str,
    priority_score: float,
    attribution_pct: float,
    peak_aqi_24h: float,
    days_since: int | None,
    dist_to_hotspot_km: float | None = None,
    spatial_score: float | None = None,
) -> str:
    days_str = f"{days_since} days" if days_since is not None else "never"
    permit_note = {
        "expired": "permit is EXPIRED (high risk)",
        "pending": "permit is PENDING renewal",
        "active": "permit is active",
    }.get(permit_status, "permit status unknown")
    spatial_note = ""
    if dist_to_hotspot_km is not None:
        spatial_note = (
            f" Spatial analysis places this source {dist_to_hotspot_km:.1f} km from the "
            f"current pollution hotspot ward (proximity score {spatial_score:.2f}/1.00)."
        )
    return (
        f"{source_name} ({source_type}) has been assigned a priority score of "
        f"{priority_score:.2f}/1.00. "
        f"This source type accounts for approximately {attribution_pct:.1f}% of current city "
        f"pollution attribution; the 24-hour peak forecast AQI is {peak_aqi_24h:.0f}."
        f"{spatial_note} "
        f"The {permit_note} and the site was last inspected {days_str} ago."
    )


async def _generate_evidence_brief(
    source_name: str,
    source_type: str,
    permit_status: str,
    priority_score: float,
    attribution_pct: float,
    peak_aqi_24h: float,
    days_since: int | None,
    dist_to_hotspot_km: float | None = None,
    spatial_score: float | None = None,
) -> str:
    """Generate evidence brief — tries Claude first, falls back to template."""
    days_str = f"{days_since} days" if days_since is not None else "never"
    spatial_detail = ""
    if dist_to_hotspot_km is not None:
        spatial_detail = (
            f"spatial proximity to worst pollution ward = {dist_to_hotspot_km:.1f} km "
            f"(proximity score {spatial_score:.2f}/1.00), "
        )
    prompt = (
        f"Write a concise 5-sentence enforcement evidence brief for an air quality inspector. "
        f"Details: source name = {source_name}, type = {source_type}, "
        f"priority score = {priority_score:.2f}/1.00, "
        f"attribution = {attribution_pct:.1f}% of city pollution by source type, "
        f"{spatial_detail}"
        f"24h peak forecast AQI = {peak_aqi_24h:.0f}, "
        f"permit status = {permit_status}, last inspected = {days_str} ago. "
        f"Be factual, concise, and professional. Do not use bullet points."
    )
    ai_text = await generate_text(
        prompt,
        system=(
            "You are an environmental compliance officer writing enforcement briefs. "
            "Produce factual, professional text only. No preamble, no headers, no lists."
        ),
        max_tokens=300,
    )
    if ai_text:
        return ai_text
    return _build_evidence_brief_template(
        source_name,
        source_type,
        permit_status,
        priority_score,
        attribution_pct,
        peak_aqi_24h,
        days_since,
        dist_to_hotspot_km=dist_to_hotspot_km,
        spatial_score=spatial_score,
    )


async def regenerate_ai_brief(
    db: AsyncSession,
    item_id: str,
    city_id: str,
) -> EnforcementItemOut | None:
    """Force-regenerate the evidence brief for an item using Claude, persist it, and return."""
    row = await repo.get_item(db, item_id, city_id)
    if not row:
        return None

    # Reconstruct the context needed to call the brief generator
    peak_aqi_24h = 200.0
    now = datetime.now(UTC)
    fc_row = await db.execute(
        text(
            """
            SELECT MAX(predicted_aqi) AS peak_aqi
            FROM forecasts
            WHERE city_id = :city_id AND is_stale = false
              AND forecast_for_ts BETWEEN :now AND :horizon
            """
        ),
        {"city_id": city_id, "now": now, "horizon": now + timedelta(hours=24)},
    )
    fc = fc_row.fetchone()
    if fc and fc[0]:
        peak_aqi_24h = float(fc[0])

    attr_row = await db.execute(
        text(
            """
            SELECT vehicular_pct, industrial_pct, construction_pct,
                   agricultural_pct, fire_pct, other_pct
            FROM attributions WHERE city_id = :city_id ORDER BY computed_at DESC LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    attr = attr_row.fetchone()
    breakdown: dict = {}
    if attr:
        breakdown = {
            "vehicular_pct": attr[0] or 0.0,
            "industrial_pct": attr[1] or 0.0,
            "construction_pct": attr[2] or 0.0,
            "agricultural_pct": attr[3] or 0.0,
            "fire_pct": attr[4] or 0.0,
            "other_pct": attr[5] or 0.0,
        }

    src_type = row["src_type"]
    src_name = row["src_name"]
    permit_status = row["src_permit_status"]
    priority_score = float(row["priority_score"])
    attribution_pct = breakdown.get(f"{src_type}_pct", 0.0)
    last_inspected_at = row.get("src_last_inspected_at")
    days_since: int | None = None
    if last_inspected_at:
        ts = (
            last_inspected_at.replace(tzinfo=UTC)
            if last_inspected_at.tzinfo is None
            else last_inspected_at
        )
        days_since = (now - ts).days

    brief = await _generate_evidence_brief(
        source_name=src_name,
        source_type=src_type,
        permit_status=permit_status,
        priority_score=priority_score,
        attribution_pct=attribution_pct,
        peak_aqi_24h=peak_aqi_24h,
        days_since=days_since,
    )
    await repo.update_evidence_brief(db, item_id, brief)
    row["evidence_brief_text"] = brief
    return _row_to_out(row)


async def rank_queue(db: AsyncSession, city_id: str) -> EnforcementListOut:
    """Re-score all active emission sources and upsert enforcement queue."""

    # 1. Fetch all emission sources with geometry
    src_rows = await db.execute(
        text(
            """
            SELECT id, name, type, permit_status, last_inspected_at,
                   ST_Y(geometry::geometry) AS src_lat,
                   ST_X(geometry::geometry) AS src_lon
            FROM emission_sources
            WHERE city_id = :city_id
            ORDER BY name
            """
        ),
        {"city_id": city_id},
    )
    sources = [dict(r._mapping) for r in src_rows.fetchall()]

    # 2. Get latest attribution breakdown
    attr_row = await db.execute(
        text(
            """
            SELECT id,
                   vehicular_pct, industrial_pct, construction_pct,
                   agricultural_pct, fire_pct, other_pct
            FROM attributions
            WHERE city_id = :city_id
            ORDER BY computed_at DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    attr = attr_row.fetchone()
    attr_id: str | None = None
    breakdown: dict = {}
    if attr:
        attr_id = attr[0]
        breakdown = {
            "vehicular_pct": attr[1] or 0.0,
            "industrial_pct": attr[2] or 0.0,
            "construction_pct": attr[3] or 0.0,
            "agricultural_pct": attr[4] or 0.0,
            "fire_pct": attr[5] or 0.0,
            "other_pct": attr[6] or 0.0,
        }

    # 3. Get peak forecast AQI over next 24h
    now = datetime.now(UTC)
    fc_row = await db.execute(
        text(
            """
            SELECT id, MAX(predicted_aqi) AS peak_aqi
            FROM forecasts
            WHERE city_id = :city_id
              AND is_stale = false
              AND forecast_for_ts BETWEEN :now AND :horizon
            GROUP BY id
            ORDER BY peak_aqi DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id, "now": now, "horizon": now + timedelta(hours=24)},
    )
    fc = fc_row.fetchone()
    forecast_id: str | None = None
    peak_aqi_24h: float = 200.0  # default moderate if no forecast
    if fc and fc[1] is not None:
        forecast_id = fc[0]
        peak_aqi_24h = float(fc[1])

    # 4a. Worst-AQI ward centroid (average station coords for the worst ward)
    worst_ward_result = await db.execute(
        text("""
            SELECT AVG(ST_Y(st.geometry::geometry)) AS lat,
                   AVG(ST_X(st.geometry::geometry)) AS lon
            FROM stations st
            JOIN station_readings sr ON sr.station_id = st.id
            WHERE st.city_id = :city_id
              AND st.ward_id IS NOT NULL
              AND sr.aqi IS NOT NULL
              AND sr.ts >= NOW() - INTERVAL '2 hours'
            GROUP BY st.ward_id
            ORDER BY AVG(sr.aqi) DESC
            LIMIT 1
        """),
        {"city_id": city_id},
    )
    worst_row = worst_ward_result.fetchone()
    worst_lat: float | None = float(worst_row[0]) if worst_row and worst_row[0] else None
    worst_lon: float | None = float(worst_row[1]) if worst_row and worst_row[1] else None

    # 4b. Current wind direction for the city
    wind_result = await db.execute(
        text(
            "SELECT wind_dir FROM weather_readings"
            " WHERE city_id = :city_id ORDER BY ts DESC LIMIT 1"
        ),
        {"city_id": city_id},
    )
    wind_row = wind_result.fetchone()
    current_wind_dir: float | None = (
        float(wind_row[0]) if wind_row and wind_row[0] is not None else None
    )

    # 5. Score each source and upsert
    scored: list[dict] = []
    for src in sources:
        # Blend: 60% category attribution + 40% spatial proximity to worst ward
        category_w = _attribution_weight(src["type"], breakdown)
        spatial_w = _spatial_proximity_score(
            src.get("src_lat"),
            src.get("src_lon"),
            worst_lat,
            worst_lon,
            current_wind_dir,
        )
        attr_w = 0.60 * category_w + 0.40 * spatial_w

        fc_w = _forecast_severity(peak_aqi_24h)
        permit_w = _permit_score(src["permit_status"])
        last_inspected_at = src["last_inspected_at"]
        days_w = _days_since_score(last_inspected_at)

        priority_score = round(
            0.35 * attr_w + 0.30 * fc_w + 0.20 * permit_w + 0.15 * days_w,
            4,
        )

        days_since: int | None = None
        if last_inspected_at:
            days_since = (
                now - last_inspected_at.replace(tzinfo=UTC)
                if last_inspected_at.tzinfo is None
                else now - last_inspected_at
            ).days

        attribution_pct = breakdown.get(f"{src['type']}_pct", 0.0)

        # Distance to worst ward (for brief context)
        src_lat, src_lon = src.get("src_lat"), src.get("src_lon")
        dist_km: float | None = None
        if src_lat and src_lon and worst_lat and worst_lon:
            dlat = math.radians(worst_lat - src_lat)
            dlon = math.radians(worst_lon - src_lon)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(src_lat))
                * math.cos(math.radians(worst_lat))
                * math.sin(dlon / 2) ** 2
            )
            dist_km = round(6371 * 2 * math.asin(math.sqrt(max(0.0, a))), 1)

        brief = await _generate_evidence_brief(
            source_name=src["name"],
            source_type=src["type"],
            permit_status=src["permit_status"],
            priority_score=priority_score,
            attribution_pct=attribution_pct,
            peak_aqi_24h=peak_aqi_24h,
            days_since=days_since,
            dist_to_hotspot_km=dist_km,
            spatial_score=round(spatial_w, 2),
        )

        item_id = await repo.upsert_queue_item(
            db=db,
            city_id=city_id,
            emission_source_id=src["id"],
            priority_score=priority_score,
            evidence_brief_text=brief,
            attribution_id=attr_id,
            forecast_id=forecast_id,
        )
        scored.append(
            {
                "id": item_id,
                "city_id": city_id,
                "emission_source_id": src["id"],
                "priority_score": priority_score,
                "evidence_brief_text": brief,
                "status": "pending",
                "attribution_id": attr_id,
                "forecast_id": forecast_id,
                "created_at": now,
                "updated_at": now,
                "src_name": src["name"],
                "src_type": src["type"],
                "src_permit_status": src["permit_status"],
                "src_last_inspected_at": last_inspected_at,
            }
        )

    await db.commit()

    scored.sort(key=lambda x: x["priority_score"], reverse=True)
    items = [_row_to_out(r) for r in scored]
    return EnforcementListOut(items=items, total=len(items))


async def get_queue(
    db: AsyncSession,
    city_id: str,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> EnforcementListOut:
    rows, total = await repo.list_queue(db, city_id, status=status, limit=limit, offset=offset)
    items = [_row_to_out(r) for r in rows]
    return EnforcementListOut(items=items, total=total)


async def get_item(db: AsyncSession, item_id: str, city_id: str) -> EnforcementItemOut | None:
    row = await repo.get_item(db, item_id, city_id)
    if not row:
        return None
    return _row_to_out(row)


async def update_status(db: AsyncSession, item_id: str, status: str) -> bool:
    return await repo.update_status(db, item_id, status)


async def count_pending(db: AsyncSession, city_id: str) -> int:
    return await repo.count_pending(db, city_id)


def _row_to_out(row: dict) -> EnforcementItemOut:
    source = EmissionSourceBrief(
        id=row["emission_source_id"],
        name=row["src_name"],
        type=row["src_type"],
        permit_status=row["src_permit_status"],
        last_inspected_at=row.get("src_last_inspected_at"),
    )
    return EnforcementItemOut(
        id=row["id"],
        city_id=row["city_id"],
        emission_source_id=row["emission_source_id"],
        priority_score=row["priority_score"],
        evidence_brief_text=row.get("evidence_brief_text"),
        status=row["status"],
        attribution_id=row.get("attribution_id"),
        forecast_id=row.get("forecast_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        source=source,
    )
