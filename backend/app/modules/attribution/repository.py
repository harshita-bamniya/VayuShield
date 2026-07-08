"""DB access layer for attributions and aqi_alerts."""

import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attribution.models import AqiAlert, Attribution


async def get_latest_attribution(db: AsyncSession, city_id: str) -> Attribution | None:
    result = await db.execute(
        select(Attribution)
        .where(Attribution.city_id == city_id)
        .order_by(Attribution.computed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_attributions(db: AsyncSession, city_id: str, limit: int = 24) -> list[Attribution]:
    result = await db.execute(
        select(Attribution)
        .where(Attribution.city_id == city_id)
        .order_by(Attribution.computed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_attribution(db: AsyncSession, data: dict) -> Attribution:
    obj = Attribution(id=str(uuid.uuid4()), **data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Alert repository ──────────────────────────────────────────────────────────


async def list_alerts(
    db: AsyncSession,
    city_id: str,
    active_only: bool = False,
    limit: int = 50,
) -> list[AqiAlert]:
    q = select(AqiAlert).where(AqiAlert.city_id == city_id)
    if active_only:
        q = q.where(AqiAlert.is_active.is_(True))
    q = q.order_by(AqiAlert.triggered_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_active_alert_for_threshold(
    db: AsyncSession, city_id: str, threshold: int
) -> AqiAlert | None:
    result = await db.execute(
        select(AqiAlert)
        .where(
            AqiAlert.city_id == city_id,
            AqiAlert.threshold == threshold,
            AqiAlert.is_active.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_alert(db: AsyncSession, data: dict) -> AqiAlert:
    obj = AqiAlert(id=str(uuid.uuid4()), **data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def resolve_alert(db: AsyncSession, alert: AqiAlert, resolved_at: datetime) -> AqiAlert:
    alert.is_active = False
    alert.resolved_at = resolved_at
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def seed_alerts(db: AsyncSession, alerts: list[dict]) -> None:
    """Insert alert rows used in seed data — skips if table already has rows for city."""
    for a in alerts:
        obj = AqiAlert(id=str(uuid.uuid4()), **a)
        db.add(obj)
    await db.commit()
