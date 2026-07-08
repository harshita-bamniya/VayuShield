"""City/Ward/Station service layer — business logic for Module 02."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.cities import repository as repo
from app.modules.cities.models import City
from app.modules.cities.schemas import CityCreate, StationCreate, WardCreate, WardOut, StationOut, CityOut
from app.schemas.common import PaginationMeta


async def list_cities(db: AsyncSession, page: int, limit: int) -> tuple[list[CityOut], PaginationMeta]:
    cities, total = await repo.get_all_cities(db, page, limit)
    return [CityOut.model_validate(c) for c in cities], PaginationMeta(page=page, limit=limit, total=total)


async def get_city(db: AsyncSession, city_id: str) -> CityOut:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    return CityOut.model_validate(city)


async def create_city(db: AsyncSession, body: CityCreate) -> CityOut:
    city = await repo.create_city(
        db,
        name=body.name,
        state=body.state,
        timezone=body.timezone,
        config_json=body.config_json,
    )
    return CityOut.model_validate(city)


async def list_wards(db: AsyncSession, city_id: str, page: int, limit: int) -> tuple[list[WardOut], PaginationMeta]:
    # Ensure city exists
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    wards, total = await repo.get_wards_for_city(db, city_id, page, limit)
    return [WardOut.model_validate(w) for w in wards], PaginationMeta(page=page, limit=limit, total=total)


async def create_ward(db: AsyncSession, city_id: str, body: WardCreate) -> WardOut:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    ward = await repo.create_ward(
        db,
        city_id=city_id,
        name=body.name,
        geometry=body.geometry,
        population=body.population,
        vulnerable_site_flags=body.vulnerable_site_flags,
    )
    return WardOut.model_validate(ward)


async def list_stations(db: AsyncSession, city_id: str, page: int, limit: int) -> tuple[list[StationOut], PaginationMeta]:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    stations, total = await repo.get_stations_for_city(db, city_id, page, limit)
    return [StationOut.model_validate(s) for s in stations], PaginationMeta(page=page, limit=limit, total=total)


async def create_station(db: AsyncSession, city_id: str, body: StationCreate) -> StationOut:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    station = await repo.create_station(
        db,
        city_id=city_id,
        ward_id=body.ward_id,
        external_station_code=body.external_station_code,
        name=body.name,
        geometry=body.geometry,
        is_active=body.is_active,
    )
    return StationOut.model_validate(station)
