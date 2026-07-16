"""City/Ward/Station repository — all DB access for Module 02."""

import json
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aqi import aqi_category as get_aqi_category
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


async def delete_city(db: AsyncSession, city_id: str) -> bool:
    city = await get_city_by_id(db, city_id)
    if not city:
        return False
    await db.delete(city)
    await db.commit()
    return True


async def create_city(
    db: AsyncSession, *, name: str, state: str, timezone: str, config_json: dict[str, Any]
) -> City:
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


async def get_wards_for_city(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[dict], int]:
    offset = (page - 1) * limit
    count_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM wards w WHERE w.city_id = :city_id"
            " AND EXISTS (SELECT 1 FROM stations s WHERE s.ward_id = w.id AND s.is_active = true)"
        ),
        {"city_id": city_id},
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
        .where(
            Ward.city_id == city_id,
            Ward.id.in_(
                text(
                    "SELECT ward_id FROM stations WHERE ward_id IS NOT NULL AND city_id = :city_id AND is_active = true"
                ).bindparams(city_id=city_id)
            ),
        )
        .offset(offset)
        .limit(limit)
    )
    wards = []
    for r in rows:
        d = dict(r._mapping)
        if d.get("geometry") and isinstance(d["geometry"], str):
            try:
                import json
                d["geometry"] = json.loads(d["geometry"])
            except (json.JSONDecodeError, ValueError):
                d["geometry"] = None
        wards.append(d)
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
    if not row:
        return None
    d = dict(row._mapping)
    if d.get("geometry") and isinstance(d["geometry"], str):
        try:
            import json
            d["geometry"] = json.loads(d["geometry"])
        except (json.JSONDecodeError, ValueError):
            d["geometry"] = None
    return d


async def get_wards_for_city_with_aqi(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[dict], int]:
    """Same as get_wards_for_city but enriched with avg AQI from latest station readings."""
    offset = (page - 1) * limit
    count_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM wards w WHERE w.city_id = :city_id"
            " AND EXISTS (SELECT 1 FROM stations s WHERE s.ward_id = w.id AND s.is_active = true)"
        ),
        {"city_id": city_id},
    )
    total = count_result.scalar_one()

    rows = await db.execute(
        text(
            """
            WITH latest_readings AS (
                SELECT DISTINCT ON (sr.station_id)
                    sr.station_id,
                    sr.aqi,
                    ST_X(s.geometry) AS lon,
                    ST_Y(s.geometry) AS lat
                FROM station_readings sr
                JOIN stations s ON s.id = sr.station_id
                WHERE s.city_id = :city_id AND s.is_active = true AND sr.aqi IS NOT NULL
                ORDER BY sr.station_id, sr.ts DESC
            ),
            ward_centroids AS (
                SELECT
                    w.id AS ward_id,
                    ST_X(ST_Centroid(w.geometry)) AS cx,
                    ST_Y(ST_Centroid(w.geometry)) AS cy
                FROM wards w
                WHERE w.city_id = :city_id AND w.geometry IS NOT NULL
            ),
            idw AS (
                SELECT
                    wc.ward_id,
                    SUM(lr.aqi / NULLIF(POWER(
                        GREATEST(ST_Distance(
                            ST_SetSRID(ST_MakePoint(wc.cx, wc.cy), 4326)::geography,
                            ST_SetSRID(ST_MakePoint(lr.lon, lr.lat), 4326)::geography
                        ) / 1000.0, 0.1), 2
                    ), 0)) /
                    SUM(1.0 / NULLIF(POWER(
                        GREATEST(ST_Distance(
                            ST_SetSRID(ST_MakePoint(wc.cx, wc.cy), 4326)::geography,
                            ST_SetSRID(ST_MakePoint(lr.lon, lr.lat), 4326)::geography
                        ) / 1000.0, 0.1), 2
                    ), 0)) AS idw_aqi
                FROM ward_centroids wc
                CROSS JOIN latest_readings lr
                GROUP BY wc.ward_id
            )
            SELECT
                w.id,
                w.city_id,
                w.name,
                w.population,
                w.vulnerable_site_flags,
                w.created_at,
                ST_AsGeoJSON(w.geometry) AS geometry,
                ROUND(COALESCE(idw.idw_aqi, direct.avg_aqi))::int AS avg_aqi
            FROM wards w
            LEFT JOIN idw ON idw.ward_id = w.id
            LEFT JOIN (
                SELECT s.ward_id, AVG(lr2.aqi)::int AS avg_aqi
                FROM (
                    SELECT DISTINCT ON (station_id) station_id, aqi
                    FROM station_readings
                    ORDER BY station_id, ts DESC
                ) lr2
                JOIN stations s ON s.id = lr2.station_id AND s.is_active = true
                WHERE s.city_id = :city_id
                GROUP BY s.ward_id
            ) direct ON direct.ward_id = w.id
            WHERE w.city_id = :city_id
              AND EXISTS (SELECT 1 FROM stations s WHERE s.ward_id = w.id AND s.is_active = true)
            ORDER BY w.name
            LIMIT :limit OFFSET :offset
            """
        ),
        {"city_id": city_id, "limit": limit, "offset": offset},
    )
    wards = []
    for r in rows:
        d = dict(r._mapping)
        avg = d.get("avg_aqi")
        d["aqi_category"] = get_aqi_category(avg) if avg is not None else None
        if d.get("geometry") and isinstance(d["geometry"], str):
            try:
                import json
                d["geometry"] = json.loads(d["geometry"])
            except (json.JSONDecodeError, ValueError):
                d["geometry"] = None
        wards.append(d)
    return wards, total


async def get_ward_detail_full(db: AsyncSession, ward_id: str) -> dict | None:
    """Ward info + latest station readings + city attribution + advisory count."""
    ward = await get_ward_by_id(db, ward_id)
    if not ward:
        return None

    # Latest station readings for stations assigned to this ward
    reading_rows = await db.execute(
        text(
            """
            SELECT DISTINCT ON (s.id)
                s.id AS station_id,
                s.name AS station_name,
                s.external_station_code,
                sr.ts,
                sr.pm25,
                sr.pm10,
                sr.aqi,
                sr.is_stale
            FROM stations s
            LEFT JOIN station_readings sr ON sr.station_id = s.id
            WHERE s.ward_id = :ward_id AND s.is_active = true
            ORDER BY s.id, sr.ts DESC NULLS LAST
            """
        ),
        {"ward_id": ward_id},
    )
    readings = []
    for r in reading_rows:
        d = dict(r._mapping)
        d["aqi_category"] = get_aqi_category(d["aqi"]) if d.get("aqi") is not None else None
        readings.append(d)

    valid_aqis = [r["aqi"] for r in readings if r.get("aqi") is not None]
    avg_aqi = round(sum(valid_aqis) / len(valid_aqis)) if valid_aqis else None

    # Latest city-level attribution breakdown
    attr_row = await db.execute(
        text(
            """
            SELECT dominant_source, vehicular_pct, industrial_pct, construction_pct,
                   agricultural_pct, fire_pct, other_pct
            FROM attributions WHERE city_id = :city_id ORDER BY computed_at DESC LIMIT 1
            """
        ),
        {"city_id": ward["city_id"]},
    )
    attr = attr_row.first()
    attribution_breakdown: dict[str, Any] = {}
    dominant_source = None
    if attr:
        a = dict(attr._mapping)
        dominant_source = a.pop("dominant_source", None)
        attribution_breakdown = {k: v for k, v in a.items() if v is not None}

    # Advisory count for this specific ward
    count_row = await db.execute(
        text("SELECT COUNT(*) FROM advisories WHERE ward_id = :ward_id"),
        {"ward_id": ward_id},
    )
    advisory_count = int(count_row.scalar() or 0)

    ward["avg_aqi"] = avg_aqi
    ward["aqi_category"] = get_aqi_category(avg_aqi) if avg_aqi is not None else None
    ward["station_readings"] = readings
    ward["attribution_breakdown"] = attribution_breakdown
    ward["dominant_source"] = dominant_source
    ward["advisory_count"] = advisory_count
    return ward


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
                INSERT INTO wards
                    (id, city_id, name, geometry, population,
                     vulnerable_site_flags, created_at, updated_at)
                VALUES
                    (:id, :city_id, :name, ST_GeomFromGeoJSON(:geom), :population,
                     CAST(:flags AS jsonb), NOW(), NOW())
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
                INSERT INTO wards
                    (id, city_id, name, population, vulnerable_site_flags, created_at, updated_at)
                VALUES
                    (:id, :city_id, :name, :population, CAST(:flags AS jsonb), NOW(), NOW())
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


async def delete_ward(db: AsyncSession, ward_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM wards WHERE id = :id RETURNING id"), {"id": ward_id}
    )
    await db.commit()
    return result.rowcount > 0


async def delete_station(db: AsyncSession, station_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM stations WHERE id = :id RETURNING id"), {"id": station_id}
    )
    await db.commit()
    return result.rowcount > 0


# ── Stations ──────────────────────────────────────────────────────────────────


async def get_stations_for_city(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[dict], int]:
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
                INSERT INTO stations
                    (id, city_id, ward_id, external_station_code, name,
                     geometry, is_active, created_at, updated_at)
                VALUES
                    (:id, :city_id, :ward_id, :code, :name,
                     ST_GeomFromGeoJSON(:geom), :is_active, NOW(), NOW())
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
                INSERT INTO stations
                    (id, city_id, ward_id, external_station_code, name,
                     is_active, created_at, updated_at)
                VALUES
                    (:id, :city_id, :ward_id, :code, :name, :is_active, NOW(), NOW())
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


async def update_station(
    db: AsyncSession,
    *,
    station_id: str,
    ward_id: str | None,
    name: str,
    is_active: bool,
) -> dict | None:
    await db.execute(
        text(
            """
            UPDATE stations
               SET ward_id   = :ward_id,
                   name      = :name,
                   is_active = :is_active,
                   updated_at = NOW()
             WHERE id = :id
            """
        ),
        {"id": station_id, "ward_id": ward_id, "name": name, "is_active": is_active},
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
    return dict(row._mapping) if row else None
