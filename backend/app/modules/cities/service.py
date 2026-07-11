"""City/Ward/Station service layer — business logic for Module 02."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.cities import repository as repo
from app.modules.cities.schemas import (
    CityCreate,
    CityOut,
    StationCreate,
    StationOut,
    StationUpdate,
    WardCreate,
    WardDetailOut,
    WardOut,
    WardWithAqiOut,
)
from app.schemas.common import PaginationMeta


async def list_cities(
    db: AsyncSession, page: int, limit: int
) -> tuple[list[CityOut], PaginationMeta]:
    cities, total = await repo.get_all_cities(db, page, limit)
    return [CityOut.model_validate(c) for c in cities], PaginationMeta(
        page=page, limit=limit, total=total
    )


async def delete_city(db: AsyncSession, city_id: str) -> None:
    deleted = await repo.delete_city(db, city_id)
    if not deleted:
        raise NotFoundError(f"City '{city_id}' not found")


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


async def list_wards(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[WardWithAqiOut], PaginationMeta]:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    wards, total = await repo.get_wards_for_city_with_aqi(db, city_id, page, limit)
    return [WardWithAqiOut.model_validate(w) for w in wards], PaginationMeta(
        page=page, limit=limit, total=total
    )


async def get_ward_detail(db: AsyncSession, city_id: str, ward_id: str) -> WardDetailOut:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    ward = await repo.get_ward_detail_full(db, ward_id)
    if not ward or ward.get("city_id") != city_id:
        raise NotFoundError(f"Ward '{ward_id}' not found in city '{city_id}'")
    return WardDetailOut.model_validate(ward)


async def _fetch_osm_boundary(ward_name: str, city_name: str) -> dict | None:
    """Query Nominatim for a ward/neighbourhood polygon. Returns GeoJSON geometry or None."""
    import httpx

    queries = [
        f"{ward_name}, {city_name}, India",
        f"{ward_name}, {city_name}",
    ]
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "VayuShield-AI/1.0"}) as client:
        for q in queries:
            try:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": q, "format": "geojson", "polygon_geojson": "1", "limit": "1"},
                )
                data = resp.json()
                features = data.get("features", [])
                if features:
                    geom = features[0].get("geometry")
                    if geom and geom.get("type") in ("Polygon", "MultiPolygon"):
                        return geom
            except Exception:
                pass
    return None


async def delete_ward(db: AsyncSession, city_id: str, ward_id: str) -> None:
    deleted = await repo.delete_ward(db, ward_id)
    if not deleted:
        raise NotFoundError(f"Ward '{ward_id}' not found")


async def delete_station(db: AsyncSession, city_id: str, station_id: str) -> None:
    deleted = await repo.delete_station(db, station_id)
    if not deleted:
        raise NotFoundError(f"Station '{station_id}' not found")


async def create_ward(db: AsyncSession, city_id: str, body: WardCreate) -> WardOut:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")

    geometry = body.geometry
    if geometry is None:
        geometry = await _fetch_osm_boundary(body.name, city.name)

    ward = await repo.create_ward(
        db,
        city_id=city_id,
        name=body.name,
        geometry=geometry,
        population=body.population,
        vulnerable_site_flags=body.vulnerable_site_flags,
    )
    return WardOut.model_validate(ward)


async def list_stations(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[StationOut], PaginationMeta]:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    stations, total = await repo.get_stations_for_city(db, city_id, page, limit)
    return [StationOut.model_validate(s) for s in stations], PaginationMeta(
        page=page, limit=limit, total=total
    )


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

    # Auto-trigger ingestion + forecast so the city shows live data immediately
    import asyncio

    asyncio.create_task(_bootstrap_city_data(city_id))

    return StationOut.model_validate(station)


async def update_station(
    db: AsyncSession, city_id: str, station_id: str, body: StationUpdate
) -> StationOut:
    city = await repo.get_city_by_id(db, city_id)
    if not city:
        raise NotFoundError(f"City '{city_id}' not found")
    # Fetch current values to fill in any fields not provided
    stations, _ = await repo.get_stations_for_city(db, city_id, page=1, limit=500)
    current = next((s for s in stations if s["id"] == station_id), None)
    if not current:
        raise NotFoundError(f"Station '{station_id}' not found in city '{city_id}'")
    updated = await repo.update_station(
        db,
        station_id=station_id,
        ward_id=body.ward_id if body.ward_id is not None else current.get("ward_id"),
        name=body.name if body.name is not None else current["name"],
        is_active=body.is_active if body.is_active is not None else current["is_active"],
    )
    if not updated:
        raise NotFoundError(f"Station '{station_id}' not found")
    return StationOut.model_validate(updated)


async def _bootstrap_city_data(city_id: str) -> None:
    """Run poll → weather → forecast → enforcement rank in the background after station creation."""
    from app.core.database import AsyncSessionLocal
    from app.core.logging import logger
    from app.modules.enforcement.service import rank_queue
    from app.modules.forecasting.service import run_forecast
    from app.modules.ingestion.service import poll_city_stations, poll_weather

    try:
        async with AsyncSessionLocal() as db:
            inserted = await poll_city_stations(db, city_id)
            logger.info("Auto-poll on station create", city_id=city_id, readings=inserted)
        async with AsyncSessionLocal() as db:
            await poll_weather(db, city_id)
        async with AsyncSessionLocal() as db:
            await run_forecast(db, city_id)
        async with AsyncSessionLocal() as db:
            await rank_queue(db, city_id)
        logger.info("Auto-bootstrap complete", city_id=city_id)
    except Exception as exc:
        from app.core.logging import logger

        logger.warning("Auto-bootstrap failed", city_id=city_id, error=str(exc))
