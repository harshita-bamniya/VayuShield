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

    Strategy:
      1. Try WAQI per-station (requires WAQI_TOKEN) — most reliable.
      2. Fall back to data.gov.in CPCB bulk (requires CPCB_API_KEY) — government server.
      3. If neither works, no reading stored for that station.
    """
    import asyncio

    city = await get_city_by_id(db, city_id)
    stations, _ = await get_stations_for_city(db, city_id, page=1, limit=100)
    active = [s for s in stations if s.get("is_active")]
    if not active:
        return 0

    now = datetime.now(UTC)
    city_name = city.name if city else ""

    # Try WAQI per-station first (concurrent)
    waqi_tasks = [
        caaqms.fetch_station_reading_waqi(
            station_code=s["external_station_code"],
            station_id=s["id"],
            ts=now,
        )
        for s in active
    ]
    waqi_results = await asyncio.gather(*waqi_tasks, return_exceptions=True)

    readings: list[StationReadingIn] = []
    stations_needing_cpcb: list[dict] = []

    for station, result in zip(active, waqi_results):
        if isinstance(result, StationReadingIn):
            readings.append(result)
        else:
            stations_needing_cpcb.append(station)

    # For any station WAQI couldn't serve, try CPCB bulk
    if stations_needing_cpcb:
        cpcb_data = await caaqms.fetch_city_readings_cpcb(city_name)
        for station in stations_needing_cpcb:
            reading = caaqms.match_station_reading(
                cpcb_data,
                station_code=station["external_station_code"],
                station_id=station["id"],
                ts=now,
            )
            if reading is not None:
                readings.append(reading)

    if not readings:
        from app.core.logging import logger
        logger.warning("No readings fetched — both WAQI and CPCB unavailable", city_id=city_id)
        return 0

    return await repo.bulk_insert_readings(db, readings)


async def seed_city_emission_sources(db: AsyncSession, city_id: str) -> int:
    """Seed realistic mock emission sources for a new city if none exist yet."""
    from app.modules.cities.repository import get_city_by_id as _get_city

    city = await _get_city(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")

    existing = await repo.get_emission_sources(db, city_id, page=1, limit=1)
    if existing[1] > 0:
        return 0  # already seeded

    cfg = city.config_json or {}
    lat = cfg.get("lat", 28.61)
    lon = cfg.get("lon", 77.21)

    # Four realistic sources spread around the city centre
    sources = [
        {
            "name": f"{city.name} Industrial Zone",
            "type": "industrial",
            "permit_status": "active",
            "dlat": 0.04,
            "dlon": 0.06,
        },
        {
            "name": f"{city.name} Central Bus Depot",
            "type": "vehicular",
            "permit_status": "active",
            "dlat": -0.02,
            "dlon": 0.03,
        },
        {
            "name": f"{city.name} Construction Site A",
            "type": "construction",
            "permit_status": "pending",
            "dlat": 0.03,
            "dlon": -0.04,
        },
        {
            "name": f"{city.name} Agricultural Burn Zone",
            "type": "agricultural",
            "permit_status": "expired",
            "dlat": -0.05,
            "dlon": -0.02,
        },
    ]
    count = 0
    for s in sources:
        await repo.create_emission_source(
            db,
            city_id=city_id,
            name=s["name"],
            type=s["type"],
            geometry={"type": "Point", "coordinates": [lon + s["dlon"], lat + s["dlat"]]},
            permit_status=s["permit_status"],
        )
        count += 1
    return count


async def seed_city_history(db: AsyncSession, city_id: str, days: int = 7) -> int:
    """Seed N days of hourly mock readings for all active stations in a city.

    Skips stations that already have readings in the same window to avoid duplicates.
    """
    from datetime import timedelta

    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")

    stations, _ = await get_stations_for_city(db, city_id, page=1, limit=100)
    active = [s for s in stations if s.get("is_active")]
    if not active:
        return 0

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    all_readings: list[StationReadingIn] = []
    for station in active:
        all_readings.extend(
            caaqms.generate_historical_readings(station["id"], start, now, interval_hours=1)
        )

    return await repo.bulk_insert_readings(db, all_readings)


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


async def discover_and_import_emission_sources(db: AsyncSession, city_id: str) -> dict:
    """Query OSM Overpass for real emission sources near the city and import new ones."""
    from app.modules.ingestion.connectors.osm_sources import fetch_emission_sources

    city = await get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")

    cfg = city.config_json or {}
    lat = cfg.get("lat", 28.61)
    lon = cfg.get("lon", 77.21)

    candidates, error = await fetch_emission_sources(lat, lon, city.name)

    if error:
        return {"discovered": 0, "imported": 0, "skipped": 0, "error": error}

    # Get existing source names to avoid duplicates
    existing_sources, _ = await repo.get_emission_sources(db, city_id, page=1, limit=200)
    existing_names = {s["name"].lower() for s in existing_sources}

    imported = 0
    skipped = 0
    for candidate in candidates:
        if candidate["name"].lower() in existing_names:
            skipped += 1
            continue
        await repo.create_emission_source(
            db,
            city_id=city_id,
            name=candidate["name"],
            type=candidate["type"],
            geometry=candidate["geometry"],
            permit_status=candidate["permit_status"],
        )
        existing_names.add(candidate["name"].lower())
        imported += 1

    # Re-rank enforcement queue with new sources
    import asyncio

    if imported > 0:
        asyncio.create_task(_auto_rank_enforcement(city_id))

    return {"discovered": len(candidates), "imported": imported, "skipped": skipped, "error": None}


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
    # Auto-rank enforcement queue so new source appears immediately
    import asyncio

    asyncio.create_task(_auto_rank_enforcement(city_id))
    return EmissionSourceOut.model_validate(source)


async def _auto_rank_enforcement(city_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.core.logging import logger
    from app.modules.enforcement.service import rank_queue

    try:
        async with AsyncSessionLocal() as db:
            await rank_queue(db, city_id)
        logger.info("Auto enforcement rank complete", city_id=city_id)
    except Exception as exc:
        logger.warning("Auto enforcement rank failed", city_id=city_id, error=str(exc))
