from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import require_city_scope
from app.core.security import require_role
from app.modules.cities import service
from app.modules.cities.schemas import (
    CityCreate,
    CityOut,
    StationCreate,
    StationOut,
    WardCreate,
    WardOut,
)
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["cities"])

# ── City endpoints (sysadmin only) ────────────────────────────────────────────


@router.get("/cities", response_model=ApiEnvelope[list[CityOut]])
async def list_cities(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    cities, meta = await service.list_cities(db, page, limit)
    return ApiEnvelope(data=cities, meta=meta)


@router.post("/cities", response_model=ApiEnvelope[CityOut], status_code=201)
async def create_city(
    body: CityCreate,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    city = await service.create_city(db, body)
    return ApiEnvelope(data=city)


@router.get("/cities/{city_id}", response_model=ApiEnvelope[CityOut])
async def get_city(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    city = await service.get_city(db, city_id)
    return ApiEnvelope(data=city)


# ── Ward endpoints ────────────────────────────────────────────────────────────


@router.get("/cities/{city_id}/wards", response_model=ApiEnvelope[list[WardOut]])
async def list_wards(
    city_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    wards, meta = await service.list_wards(db, city_id, page, limit)
    return ApiEnvelope(data=wards, meta=meta)


@router.post("/cities/{city_id}/wards", response_model=ApiEnvelope[WardOut], status_code=201)
async def create_ward(
    city_id: str,
    body: WardCreate,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    ward = await service.create_ward(db, city_id, body)
    return ApiEnvelope(data=ward)


# ── Station endpoints ─────────────────────────────────────────────────────────


@router.get("/cities/{city_id}/stations", response_model=ApiEnvelope[list[StationOut]])
async def list_stations(
    city_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    stations, meta = await service.list_stations(db, city_id, page, limit)
    return ApiEnvelope(data=stations, meta=meta)


@router.post("/cities/{city_id}/stations", response_model=ApiEnvelope[StationOut], status_code=201)
async def create_station(
    city_id: str,
    body: StationCreate,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    station = await service.create_station(db, city_id, body)
    return ApiEnvelope(data=station)
