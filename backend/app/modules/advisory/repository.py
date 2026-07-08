import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_advisories(
    db: AsyncSession,
    city_id: str,
    language: str | None = None,
    channel: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    filters = "WHERE city_id = :city_id"
    params: dict = {"city_id": city_id, "limit": limit, "offset": offset}
    if language:
        filters += " AND language = :language"
        params["language"] = language
    if channel:
        filters += " AND channel = :channel"
        params["channel"] = channel

    count_row = await db.execute(text(f"SELECT COUNT(*) FROM advisories {filters}"), params)
    total = count_row.scalar() or 0

    rows = await db.execute(
        text(
            f"""
            SELECT id, city_id, ward_id, language, title, body,
                   aqi_level, dominant_source, channel, sent_at, created_at
            FROM advisories
            {filters}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return [dict(r._mapping) for r in rows.fetchall()], total


async def get_advisory(db: AsyncSession, advisory_id: str, city_id: str) -> dict | None:
    row = await db.execute(
        text(
            """
            SELECT id, city_id, ward_id, language, title, body,
                   aqi_level, dominant_source, channel, sent_at, created_at
            FROM advisories
            WHERE id = :id AND city_id = :city_id
            """
        ),
        {"id": advisory_id, "city_id": city_id},
    )
    r = row.fetchone()
    return dict(r._mapping) if r else None


async def advisory_exists_today(
    db: AsyncSession, city_id: str, aqi_level: str, language: str
) -> bool:
    """Check if an advisory for this city/aqi_level/language was already created today."""
    row = await db.execute(
        text(
            """
            SELECT id FROM advisories
            WHERE city_id = :city_id
              AND aqi_level = :aqi_level
              AND language = :language
              AND created_at >= DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')
            LIMIT 1
            """
        ),
        {"city_id": city_id, "aqi_level": aqi_level, "language": language},
    )
    return row.fetchone() is not None


async def create_advisory(
    db: AsyncSession,
    city_id: str,
    language: str,
    title: str,
    body: str,
    aqi_level: str,
    dominant_source: str | None,
    channel: str = "web",
    ward_id: str | None = None,
) -> dict:
    advisory_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    await db.execute(
        text(
            """
            INSERT INTO advisories
                (id, city_id, ward_id, language, title, body,
                 aqi_level, dominant_source, channel, sent_at, created_at)
            VALUES
                (:id, :city_id, :ward_id, :language, :title, :body,
                 :aqi_level, :dominant_source, :channel, NULL, :created_at)
            """
        ),
        {
            "id": advisory_id,
            "city_id": city_id,
            "ward_id": ward_id,
            "language": language,
            "title": title,
            "body": body,
            "aqi_level": aqi_level,
            "dominant_source": dominant_source,
            "channel": channel,
            "created_at": now,
        },
    )
    return {
        "id": advisory_id,
        "city_id": city_id,
        "ward_id": ward_id,
        "language": language,
        "title": title,
        "body": body,
        "aqi_level": aqi_level,
        "dominant_source": dominant_source,
        "channel": channel,
        "sent_at": None,
        "created_at": now,
    }


async def count_advisories(db: AsyncSession, city_id: str) -> int:
    row = await db.execute(
        text("SELECT COUNT(*) FROM advisories WHERE city_id = :city_id"),
        {"city_id": city_id},
    )
    return row.scalar() or 0
