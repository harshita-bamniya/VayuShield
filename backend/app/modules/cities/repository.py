"""City/Ward/Station repository — all DB access for Module 02."""

import json
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cities.models import City, Station, Ward


# ── Cities ────────────────────────────────────────────────────────────────────

async def get_all_cities(db: AsyncSession, page: int, limit: int) -> tuple[list[City], int]:
    offset = (page - 1) * limit
    count_result = await db.execute(select(func.count()).select_from(City))
    total = count_result.scalar_one()
    result = await db.execute(select(City).offset(offset).limit(limit))
    cities = list(result.scalars().all())
    return cities, total


async def get_city_by_id(db: AsyncSession, city_id: str) -> City | None:
    result = await db.execute(select(City).where(City.id == city_id))
    return result.scalar_one_or_none()


async def create_city(db: AsyncSession, *, name: str, state: str, timezone: str, config_json: dict[str, Any]) -> City:
    city = City(
        id=str(uuid.uuid4()),
        name=name,
        state=state,
        timezone=timezone,
        config_json=config_json,
    )
    db.add(city)
    await db.commit()
    await db.refresh(city)
    return city


# ── Wards ─────────────────────────────────────────────────────────────────────

async def get_wards_for_city(db: AsyncSession, city_id: str, page: int, limit: int) -> tuple[list[dict], int]:
    offset = (page - 1) * limit
    count_result = await db.execute(
        select(func.count()).select_from(Ward).where(Ward.city_id == city_id)
    )
    total = count_result.scalar_one()

    # Cast geometry to GeoJSON string so the Pydantic schema can parse it
    rows = await db.execute(
        select(
            Ward.id,
            Ward.city_id,
            Ward.name,
            Ward.population,
            Ward.vulnerable_site_flags,
            Ward.created_at,
            func.ST_AsGeoJSON(Ward.geometry).label("geometry"),
        )
        .where(Ward.city_id == city_id)
        .offset(offset)
        .limit(limit)
    )
    wards = [dict(r._mapping) for r in rows]
    return wards, total


async def get_ward_by_id(db: AsyncSession, ward_id: str) -> dict | None:
    rows = await db.execute(
        select(
            Ward.id,
            Ward.city_id,
            Ward.name,
            Ward.population,
            Ward.vulnerable_site_flags,
            Ward.created_at,
            func.ST_AsGeoJSON(Ward.geometry).label("geometry"),
        ).where(Ward.id == ward_id)
    )
    row = rows.first()
    return dict(row._mapping) if row else None


async def create_ward(
    db: AsyncSession,
    *,
    city_id: str,
    name: str,
    geometry: dict | None,
    population: int | None,
    vulnerable_site_flags: dict,
) -> dict:
    ward_id = str(uuid.uuid4())
    if geometry:
        await db.execute(
            text(
                """
                INSERT INTO wards (id, city_id, name, geometry, population, vulnerable_site_flags, created_at, updated_at)
                VALUES (:id, :city_id, :name, ST_GeomFromGeoJSON(:geom), :population, :flags::jsonb, NOW(), NOW())
                """
            ),
            {
                "id": ward_id,
                "city_id": city_id,
                "name": name,
                "geom": json.dumps(geometry),
                "population": population,
                "flags": json.dumps(vulnerable_site_flags),
            },
        )
    else:
        await db.execute(
            text(
                """
                INSERT INTO wards (id, city_id, name, population, vulnerable_site_flags, created_at, updated_at)
                VALUES (:id, :city_id, :name, :population, :flags::jsonb, NOW(), NOW())
                """
            ),
            {
                "id": ward_id,
                "city_id": city_id,
                "name": name,
                "population": population,
                "flags": json.dumps(vulnerable_site_flags),
            },
        )
    await db.commit()
    ward = await get_ward_by_id(db, ward_id)
    return ward  # type: ignore[return-value]


# ── Stations ──────────────────────────────────────────────────────────────────

async def get_stations_for_city(db: AsyncSession, city_id: str, page: int, limit: int) -> tuple[list[dict], int]:
    offset = (page - 1) * limit
    count_result = await db.execute(
        select(func.count()).select_from(Station).where(Station.city_id == city_id)
    )
    total = count_result.scalar_one()

    rows = await db.execute(
        select(
            Station.id,
            Station.city_id,
            Station.ward_id,
            Station.external_station_code,
            Station.name,
            Station.is_active,
            Station.created_at,
            func.ST_AsGeoJSON(Station.geometry).label("geometry"),
        )
        .where(Station.city_id == city_id)
        .offset(offset)
        .limit(limit)
    )
    stations = [dict(r._mapping) for r in rows]
    return stations, total


async def create_station(
    db: AsyncSession,
    *,
    city_id: str,
    ward_id: str | None,
    external_station_code: str,
    name: str,
    geometry: dict | None,
    is_active: bool,
) -> dict:
    station_id = str(uuid.uuid4())
    if geometry:
        await db.execute(
            text(
                """
                INSERT INTO stations (id, city_id, ward_id, external_station_code, name, geometry, is_active, created_at, updated_at)
                VALUES (:id, :city_id, :ward_id, :code, :name, ST_GeomFromGeoJSON(:geom), :is_active, NOW(), NOW())
                """
            ),
            {
                "id": station_id,
                "city_id": city_id,
                "ward_id": ward_id,
                "code": external_station_code,
                "name": name,
                "geom": json.dumps(geometry),
                "is_active": is_active,
            },
        )
    else:
        await db.execute(
            text(
                """
                INSERT INTO stations (id, city_id, ward_id, external_station_code, name, is_active, created_at, updated_at)
                VALUES (:id, :city_id, :ward_id, :code, :name, :is_active, NOW(), NOW())
                """
            ),
            {
                "id": station_id,
                "city_id": city_id,
                "ward_id": ward_id,
                "code": external_station_code,
                "name": name,
                "is_active": is_active,
            },
        )
    await db.commit()

    rows = await db.execute(
        select(
            Station.id,
            Station.city_id,
            Station.ward_id,
            Station.external_station_code,
            Station.name,
            Station.is_active,
            Station.created_at,
            func.ST_AsGeoJSON(Station.geometry).label("geometry"),
        ).where(Station.id == station_id)
    )
    row = rows.first()
    return dict(row._mapping) if row else {}
