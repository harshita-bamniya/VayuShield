from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import require_city_scope
from app.core.security import require_role
from app.modules.ingestion import service
from app.modules.ingestion.schemas import (
    EmissionSourceCreate,
    EmissionSourceOut,
    FireHotspotApiOut,
    LatestReadingOut,
    WeatherReadingOut,
)
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["ingestion"])


# ── Station readings ──────────────────────────────────────────────────────────


@router.get(
    "/cities/{city_id}/readings/latest",
    response_model=ApiEnvelope[list[LatestReadingOut]],
)
async def latest_readings(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Latest reading from every active station in the city."""
    readings = await service.get_latest_readings(db, city_id)
    return ApiEnvelope(data=readings)


@router.get(
    "/cities/{city_id}/stations/{station_id}/readings",
    response_model=ApiEnvelope[list[dict]],
)
async def station_readings(
    city_id: str,
    station_id: str,
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    readings, meta = await service.get_station_readings(
        db, city_id, station_id, since, until, page, limit
    )
    return ApiEnvelope(data=readings, meta=meta)


@router.post("/cities/{city_id}/readings/poll", response_model=ApiEnvelope[dict])
async def trigger_poll(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin", "admin")),
):
    """Manually trigger a station poll cycle for a city (sysadmin/admin only)."""
    inserted = await service.poll_city_stations(db, city_id)
    return ApiEnvelope(data={"inserted": inserted})


@router.post("/cities/{city_id}/emission-sources/seed", response_model=ApiEnvelope[dict])
async def seed_emission_sources(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    """Seed 4 realistic mock emission sources for a new city (skips if already seeded)."""
    count = await service.seed_city_emission_sources(db, city_id)
    return ApiEnvelope(data={"seeded": count})


@router.post("/cities/{city_id}/readings/seed-history", response_model=ApiEnvelope[dict])
async def seed_history(
    city_id: str,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    """Seed N days of hourly mock readings for all active stations in a city.

    Used to bootstrap new cities so the forecast model has enough history to work from.
    """
    inserted = await service.seed_city_history(db, city_id, days)
    return ApiEnvelope(data={"inserted": inserted})


# ── Weather ───────────────────────────────────────────────────────────────────


@router.get(
    "/cities/{city_id}/weather/latest",
    response_model=ApiEnvelope[WeatherReadingOut | None],
)
async def latest_weather(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    weather = await service.get_latest_weather(db, city_id)
    return ApiEnvelope(data=weather)


@router.post("/cities/{city_id}/weather/poll", response_model=ApiEnvelope[dict])
async def trigger_weather_poll(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin", "admin")),
):
    inserted = await service.poll_weather(db, city_id)
    return ApiEnvelope(data={"inserted": inserted})


# ── Fire Hotspots ─────────────────────────────────────────────────────────────


@router.get(
    "/cities/{city_id}/fire-hotspots",
    response_model=ApiEnvelope[list[FireHotspotApiOut]],
)
async def list_fire_hotspots(
    city_id: str,
    hours_back: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Fire hotspots detected within the last N hours for a city."""
    hotspots = await service.get_fire_hotspots(db, city_id, hours_back)
    return ApiEnvelope(data=hotspots)


# ── Emission Sources ──────────────────────────────────────────────────────────


@router.get(
    "/cities/{city_id}/emission-sources",
    response_model=ApiEnvelope[list[EmissionSourceOut]],
)
async def list_emission_sources(
    city_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    sources, meta = await service.list_emission_sources(db, city_id, page, limit)
    return ApiEnvelope(data=sources, meta=meta)


@router.post(
    "/cities/{city_id}/emission-sources/discover",
    response_model=ApiEnvelope[dict],
)
async def discover_emission_sources(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin", "admin")),
):
    """Auto-discover emission sources from OpenStreetMap and insert new ones."""
    result = await service.discover_and_import_emission_sources(db, city_id)
    return ApiEnvelope(data=result)


@router.post(
    "/cities/{city_id}/emission-sources",
    response_model=ApiEnvelope[EmissionSourceOut],
    status_code=201,
)
async def create_emission_source(
    city_id: str,
    body: EmissionSourceCreate,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin", "admin")),
):
    source = await service.create_emission_source(db, city_id, body)
    return ApiEnvelope(data=source)
