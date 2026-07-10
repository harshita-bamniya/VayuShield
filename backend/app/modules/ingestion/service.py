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
    """Pull latest readings from all active stations in a city. Returns total inserted.

    Tries the CPCB data.gov.in API first (bulk fetch for the city); falls back to
    mock data per-station when the API is unavailable or a station is unmatched.
    """
    city = await get_city_by_id(db, city_id)
    stations, _ = await get_stations_for_city(db, city_id, page=1, limit=100)
    active = [s for s in stations if s.get("is_active")]
    if not active:
        return 0

    now = datetime.now(UTC)

    # Bulk fetch from CPCB (returns {} when key not set or call fails)
    city_name = city.name if city else ""
    cpcb_data = await caaqms.fetch_city_readings_cpcb(city_name)

    readings: list[StationReadingIn] = []
    for station in active:
        reading = caaqms.match_station_reading(
            cpcb_data,
            station_code=station["external_station_code"],
            station_id=station["id"],
            ts=now,
        )
        if reading is None:
            # Fall back to mock
            reading = await caaqms.fetch_station_readings(
                station_code=station["external_station_code"],
                station_id=station["id"],
                ts=now,
            )
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
    from app.modules.ingestion.connectors.weather import DELHI_LAT, DELHI_LON, fetch_weather

    cfg = city.config_json or {}
    lat = cfg.get("lat", DELHI_LAT)
    lon = cfg.get("lon", DELHI_LON)
    readings = await fetch_weather(lat, lon, city_id, hours_back=2)
    return await repo.bulk_insert_weather(db, readings)


async def get_latest_weather(db: AsyncSession, city_id: str) -> WeatherReadingOut | None:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    row = await repo.get_latest_weather(db, city_id)
    return WeatherReadingOut(**row) if row else None


# ── Fire Hotspots ─────────────────────────────────────────────────────────────


async def get_fire_hotspots(db: AsyncSession, city_id: str, hours_back: int = 24) -> list[dict]:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    return await repo.get_fire_hotspots_with_coords(db, city_id, hours_back)


async def poll_fire_hotspots(db: AsyncSession, city_id: str) -> int:
    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    from app.modules.ingestion.connectors.fire_hotspots import DELHI_BBOX

    cfg = city.config_json or {}
    lat = cfg.get("lat")
    lon = cfg.get("lon")
    if lat is not None and lon is not None:
        bbox = (lat - 0.5, lat + 0.5, lon - 0.5, lon + 0.5)
    else:
        bbox = DELHI_BBOX
    hotspots = await fire_connector.fetch_fire_hotspots(city_id, bbox=bbox)
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
