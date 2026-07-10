"""RQ background jobs for data ingestion (Module 03).

These functions are enqueued by the scheduler (or triggered manually) and run
inside Docker where Redis and the DB are available.

Job schedule (configured in docker-compose via rq-scheduler or a cron container):
  - poll_all_stations_job  → every 15 minutes
  - poll_weather_job       → every hour
  - poll_fire_hotspots_job → every hour

Usage:
    from rq import Queue
    from redis import Redis
    q = Queue(connection=Redis.from_url(settings.REDIS_URL))
    q.enqueue(poll_all_stations_job, city_id="...")
"""

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.modules.cities.models import City
from app.modules.ingestion.service import poll_city_stations, poll_fire_hotspots, poll_weather


def _run(coro):
    """Run an async coroutine from a sync RQ job context."""
    return asyncio.run(coro)


async def _get_all_city_ids(db) -> list[str]:
    result = await db.execute(select(City.id))
    return [row[0] for row in result.all()]


def poll_all_stations_job(city_id: str | None = None) -> dict:
    """RQ job: fetch latest readings from all CAAQMS stations.

    When city_id is given, polls only that city. Otherwise polls every city in the DB.
    """

    async def _inner():
        async with AsyncSessionLocal() as db:
            ids = [city_id] if city_id else await _get_all_city_ids(db)
            total = 0
            for cid in ids:
                inserted = await poll_city_stations(db, cid)
                logger.info("Station poll complete", city_id=cid, inserted=inserted)
                total += inserted
            return {"city_ids": ids, "inserted": total}

    return _run(_inner())


def poll_weather_job(city_id: str | None = None) -> dict:
    """RQ job: fetch hourly weather from Open-Meteo for all cities (or one)."""

    async def _inner():
        async with AsyncSessionLocal() as db:
            ids = [city_id] if city_id else await _get_all_city_ids(db)
            total = 0
            for cid in ids:
                inserted = await poll_weather(db, cid)
                logger.info("Weather poll complete", city_id=cid, inserted=inserted)
                total += inserted
            return {"city_ids": ids, "inserted": total}

    return _run(_inner())


def poll_fire_hotspots_job(city_id: str | None = None) -> dict:
    """RQ job: fetch NASA FIRMS fire detections for all cities (or one)."""

    async def _inner():
        async with AsyncSessionLocal() as db:
            ids = [city_id] if city_id else await _get_all_city_ids(db)
            total = 0
            for cid in ids:
                inserted = await poll_fire_hotspots(db, cid)
                logger.info("Fire hotspot poll complete", city_id=cid, inserted=inserted)
                total += inserted
            return {"city_ids": ids, "inserted": total}

    return _run(_inner())
