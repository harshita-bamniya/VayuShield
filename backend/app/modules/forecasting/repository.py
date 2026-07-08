"""DB access layer for the forecasts table."""

import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forecasting.models import Forecast


async def get_latest_forecast_run(
    db: AsyncSession, city_id: str
) -> tuple[datetime | None, list[Forecast]]:
    """Return (generated_at, points) for the most recent forecast run."""
    # Find latest generated_at for this city
    result = await db.execute(
        text(
            "SELECT MAX(generated_at) FROM forecasts WHERE city_id = :city_id"
        ),
        {"city_id": city_id},
    )
    latest_gen = result.scalar_one_or_none()
    if latest_gen is None:
        return None, []

    points_result = await db.execute(
        select(Forecast)
        .where(Forecast.city_id == city_id, Forecast.generated_at == latest_gen)
        .order_by(Forecast.forecast_for_ts)
    )
    return latest_gen, list(points_result.scalars().all())


async def mark_previous_stale(db: AsyncSession, city_id: str) -> None:
    """Mark all previous forecast rows for this city as stale before inserting new ones."""
    await db.execute(
        text("UPDATE forecasts SET is_stale = true WHERE city_id = :city_id AND is_stale = false"),
        {"city_id": city_id},
    )
    await db.commit()


async def bulk_insert_forecast(db: AsyncSession, rows: list[dict]) -> list[Forecast]:
    """Insert a batch of forecast rows and return ORM objects."""
    objs = [Forecast(id=str(uuid.uuid4()), **r) for r in rows]
    for obj in objs:
        db.add(obj)
    await db.commit()
    for obj in objs:
        await db.refresh(obj)
    return objs
