"""Enforcement queue — database access layer."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enforcement.models import Inspection


async def list_queue(
    db: AsyncSession,
    city_id: str,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    where = "eq.city_id = :city_id"
    params: dict = {"city_id": city_id, "limit": limit, "offset": offset}
    if status:
        where += " AND eq.status = :status"
        params["status"] = status

    rows = await db.execute(
        text(
            f"""
            SELECT
                eq.id, eq.city_id, eq.emission_source_id, eq.priority_score,
                eq.evidence_brief_text, eq.status, eq.attribution_id, eq.forecast_id,
                eq.created_at, eq.updated_at,
                es.name   AS src_name,
                es.type   AS src_type,
                es.permit_status AS src_permit_status,
                es.last_inspected_at AS src_last_inspected_at
            FROM enforcement_queue eq
            JOIN emission_sources es ON es.id = eq.emission_source_id
            WHERE {where}
            ORDER BY eq.priority_score DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    items = [dict(r._mapping) for r in rows.fetchall()]

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM enforcement_queue eq WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_row.scalar() or 0
    return items, int(total)


async def get_item(db: AsyncSession, item_id: str, city_id: str) -> dict | None:
    row = await db.execute(
        text(
            """
            SELECT
                eq.id, eq.city_id, eq.emission_source_id, eq.priority_score,
                eq.evidence_brief_text, eq.status, eq.attribution_id, eq.forecast_id,
                eq.created_at, eq.updated_at,
                es.name   AS src_name,
                es.type   AS src_type,
                es.permit_status AS src_permit_status,
                es.last_inspected_at AS src_last_inspected_at
            FROM enforcement_queue eq
            JOIN emission_sources es ON es.id = eq.emission_source_id
            WHERE eq.id = :id AND eq.city_id = :city_id
            """
        ),
        {"id": item_id, "city_id": city_id},
    )
    r = row.fetchone()
    return dict(r._mapping) if r else None


async def upsert_queue_item(
    db: AsyncSession,
    city_id: str,
    emission_source_id: str,
    priority_score: float,
    evidence_brief_text: str,
    attribution_id: str | None,
    forecast_id: str | None,
) -> str:
    existing = await db.execute(
        text(
            "SELECT id FROM enforcement_queue "
            "WHERE city_id = :city_id AND emission_source_id = :src_id AND status = 'pending'"
        ),
        {"city_id": city_id, "src_id": emission_source_id},
    )
    row = existing.fetchone()
    if row:
        item_id = row[0]
        await db.execute(
            text(
                """
                UPDATE enforcement_queue
                SET priority_score = :score,
                    evidence_brief_text = :brief,
                    attribution_id = :attr_id,
                    forecast_id = :fc_id,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": item_id,
                "score": priority_score,
                "brief": evidence_brief_text,
                "attr_id": attribution_id,
                "fc_id": forecast_id,
            },
        )
        return item_id
    else:
        item_id = str(uuid.uuid4())
        await db.execute(
            text(
                """
                INSERT INTO enforcement_queue
                    (id, city_id, emission_source_id, priority_score,
                     evidence_brief_text, status, attribution_id, forecast_id,
                     created_at, updated_at)
                VALUES
                    (:id, :city_id, :src_id, :score,
                     :brief, 'pending', :attr_id, :fc_id,
                     NOW(), NOW())
                """
            ),
            {
                "id": item_id,
                "city_id": city_id,
                "src_id": emission_source_id,
                "score": priority_score,
                "brief": evidence_brief_text,
                "attr_id": attribution_id,
                "fc_id": forecast_id,
            },
        )
        return item_id


async def update_status(db: AsyncSession, item_id: str, status: str) -> bool:
    result = await db.execute(
        text("UPDATE enforcement_queue SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"status": status, "id": item_id},
    )
    await db.commit()
    return result.rowcount > 0


async def count_pending(db: AsyncSession, city_id: str) -> int:
    row = await db.execute(
        text(
            "SELECT COUNT(*) FROM enforcement_queue WHERE city_id = :city_id AND status = 'pending'"
        ),
        {"city_id": city_id},
    )
    return int(row.scalar() or 0)


async def create_inspection(
    db: AsyncSession,
    queue_item_id: str,
    inspector_id: str | None,
    data: dict,
) -> Inspection:
    insp = Inspection(
        id=str(uuid.uuid4()),
        enforcement_queue_id=queue_item_id,
        inspector_id=inspector_id,
        scheduled_at=data.get("scheduled_at"),
        completed_at=data.get("completed_at"),
        outcome=data.get("outcome"),
        notes=data.get("notes"),
    )
    db.add(insp)

    if data.get("completed_at"):
        await db.execute(
            text(
                "UPDATE emission_sources SET last_inspected_at = :ts, updated_at = NOW() "
                "WHERE id = (SELECT emission_source_id FROM enforcement_queue WHERE id = :qid)"
            ),
            {"ts": data["completed_at"], "qid": queue_item_id},
        )

    await db.commit()
    await db.refresh(insp)
    return insp
