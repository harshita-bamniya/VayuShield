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

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.modules.ingestion.service import poll_city_stations, poll_fire_hotspots, poll_weather

# The pilot city ID matches the seed constant in seed.py
DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _run(coro):
    """Run an async coroutine from a sync RQ job context."""
    return asyncio.run(coro)


def poll_all_stations_job(city_id: str = DELHI_CITY_ID) -> dict:
    """RQ job: fetch latest readings from all CAAQMS stations for a city."""

    async def _inner():
        async with AsyncSessionLocal() as db:
            inserted = await poll_city_stations(db, city_id)
            logger.info("Station poll complete", city_id=city_id, inserted=inserted)
            return {"city_id": city_id, "inserted": inserted}

    return _run(_inner())


def poll_weather_job(city_id: str = DELHI_CITY_ID) -> dict:
    """RQ job: fetch hourly weather from Open-Meteo for a city."""

    async def _inner():
        async with AsyncSessionLocal() as db:
            inserted = await poll_weather(db, city_id)
            logger.info("Weather poll complete", city_id=city_id, inserted=inserted)
            return {"city_id": city_id, "inserted": inserted}

    return _run(_inner())


def poll_fire_hotspots_job(city_id: str = DELHI_CITY_ID) -> dict:
    """RQ job: fetch NASA FIRMS fire detections within city bounding box."""

    async def _inner():
        async with AsyncSessionLocal() as db:
            inserted = await poll_fire_hotspots(db, city_id)
            logger.info("Fire hotspot poll complete", city_id=city_id, inserted=inserted)
            return {"city_id": city_id, "inserted": inserted}

    return _run(_inner())
