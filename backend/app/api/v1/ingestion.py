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
    LatestReadingOut,
    WeatherReadingOut,
)
from app.schemas.common import ApiEnvelope, PaginationMeta

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
