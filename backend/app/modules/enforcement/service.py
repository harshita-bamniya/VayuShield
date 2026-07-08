"""Enforcement Agent — priority scoring and evidence brief generation.

Scoring formula:
    priority_score = 0.35 × source_attribution
                   + 0.30 × forecast_severity
                   + 0.20 × permit_status
                   + 0.15 × days_since_inspection
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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


def _build_evidence_brief(
    source_name: str,
    source_type: str,
    permit_status: str,
    priority_score: float,
    attribution_pct: float,
    peak_aqi_24h: float,
    days_since: int | None,
) -> str:
    days_str = f"{days_since} days" if days_since is not None else "never"
    permit_note = {
        "expired": "permit is EXPIRED (high risk)",
        "pending": "permit is PENDING renewal",
        "active": "permit is active",
    }.get(permit_status, "permit status unknown")
    return (
        f"{source_name} ({source_type}) has been assigned a priority score of "
        f"{priority_score:.2f}/1.00. "
        f"This source accounts for approximately {attribution_pct:.1f}% of current city "
        f"pollution attribution; the 24-hour peak forecast AQI is {peak_aqi_24h:.0f}. "
        f"The {permit_note} and the site was last inspected {days_str} ago."
    )


async def rank_queue(db: AsyncSession, city_id: str) -> EnforcementListOut:
    """Re-score all active emission sources and upsert enforcement queue."""

    # 1. Fetch all emission sources for city
    src_rows = await db.execute(
        text(
            """
            SELECT id, name, type, permit_status, last_inspected_at
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

    # 4. Score each source and upsert
    scored: list[dict] = []
    for src in sources:
        attr_w = _attribution_weight(src["type"], breakdown)
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
        brief = _build_evidence_brief(
            source_name=src["name"],
            source_type=src["type"],
            permit_status=src["permit_status"],
            priority_score=priority_score,
            attribution_pct=attribution_pct,
            peak_aqi_24h=peak_aqi_24h,
            days_since=days_since,
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
