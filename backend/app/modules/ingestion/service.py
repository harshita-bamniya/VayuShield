"""Ingestion service layer — orchestrates connectors → repository for Module 03."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.cities.repository import get_city_by_id, get_stations_for_city
from app.modules.ingestion import repository as repo
from app.modules.ingestion.connectors import (
    caaqms,
)
from app.modules.ingestion.connectors import (
    fire_hotspots as fire_connector,
)
from app.modules.ingestion.schemas import (
    EmissionSourceCreate,
    EmissionSourceOut,
    LatestReadingOut,
    StationReadingIn,
    WeatherReadingOut,
)
from app.schemas.common import PaginationMeta

# ── Station readings ──────────────────────────────────────────────────────────


async def poll_city_stations(db: AsyncSession, city_id: str) -> int:
    """Pull latest readings from all active stations in a city. Returns total inserted."""
    stations, _ = await get_stations_for_city(db, city_id, page=1, limit=100)
    now = datetime.now(UTC)
    readings: list[StationReadingIn] = []
    for station in stations:
        if not station.get("is_active"):
            continue
        reading = await caaqms.fetch_station_readings(
            station_code=station["external_station_code"],
            station_id=station["id"],
            ts=now,
        )
        if reading:
            readings.append(reading)
    return await repo.bulk_insert_readings(db, readings)


async def get_latest_readings(db: AsyncSession, city_id: str) -> list[LatestReadingOut]:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    rows = await repo.get_latest_readings_for_city(db, city_id)
    return [LatestReadingOut(**r) for r in rows]


async def get_station_readings(
    db: AsyncSession,
    city_id: str,
    station_id: str,
    since: datetime | None,
    until: datetime | None,
    page: int,
    limit: int,
) -> tuple[list[dict], PaginationMeta]:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    readings, total = await repo.get_readings_for_station(db, station_id, since, until, page, limit)
    return readings, PaginationMeta(page=page, limit=limit, total=total)


# ── Weather ───────────────────────────────────────────────────────────────────


async def poll_weather(db: AsyncSession, city_id: str) -> int:
    """Fetch latest weather for city from Open-Meteo. Returns rows inserted."""
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    # Use city centroid — for now hardcoded to Delhi; Module 11 will store lat/lon in config_json
    from app.modules.ingestion.connectors.weather import fetch_weather_for_delhi

    readings = await fetch_weather_for_delhi(city_id, hours_back=2)
    return await repo.bulk_insert_weather(db, readings)


async def get_latest_weather(db: AsyncSession, city_id: str) -> WeatherReadingOut | None:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    row = await repo.get_latest_weather(db, city_id)
    return WeatherReadingOut(**row) if row else None


# ── Fire Hotspots ─────────────────────────────────────────────────────────────


async def poll_fire_hotspots(db: AsyncSession, city_id: str) -> int:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    hotspots = await fire_connector.fetch_fire_hotspots(city_id)
    inserted = 0
    for h in hotspots:
        await repo.insert_fire_hotspot(db, **h)
        inserted += 1
    return inserted


# ── Emission Sources ──────────────────────────────────────────────────────────


async def list_emission_sources(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[EmissionSourceOut], PaginationMeta]:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    sources, total = await repo.get_emission_sources(db, city_id, page, limit)
    return [EmissionSourceOut.model_validate(s) for s in sources], PaginationMeta(
        page=page, limit=limit, total=total
    )


async def create_emission_source(
    db: AsyncSession, city_id: str, body: EmissionSourceCreate
) -> EmissionSourceOut:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    source = await repo.create_emission_source(
        db,
        city_id=city_id,
        name=body.name,
        type=body.type,
        geometry=body.geometry,
        permit_status=body.permit_status,
    )
    return EmissionSourceOut.model_validate(source)
