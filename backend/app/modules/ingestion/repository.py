"""Ingestion repository — all DB reads/writes for Module 03."""

import json
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aqi import aqi_category, compute_aqi
from app.modules.ingestion.schemas import StationReadingIn

# ── Station Readings ──────────────────────────────────────────────────────────


async def bulk_insert_readings(db: AsyncSession, readings: list[StationReadingIn]) -> int:
    """Insert a batch of station readings. Returns count inserted."""
    if not readings:
        return 0
    inserted = 0
    for r in readings:
        aqi = compute_aqi(r.pm25, r.pm10)
        await db.execute(
            text(
                """
                INSERT INTO station_readings
                    (id, station_id, ts, pm25, pm10, no2, so2, co, o3, aqi, is_stale)
                VALUES
                    (:id, :station_id, :ts, :pm25, :pm10, :no2, :so2, :co, :o3, :aqi, false)
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "station_id": r.station_id,
                "ts": r.ts,
                "pm25": r.pm25,
                "pm10": r.pm10,
                "no2": r.no2,
                "so2": r.so2,
                "co": r.co,
                "o3": r.o3,
                "aqi": aqi,
            },
        )
        inserted += 1
    await db.commit()
    return inserted


async def get_latest_readings_for_city(db: AsyncSession, city_id: str) -> list[dict]:
    """Return the most recent reading for each active station in the city."""
    rows = await db.execute(
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
            WHERE s.city_id = :city_id AND s.is_active = true
            ORDER BY s.id, sr.ts DESC NULLS LAST
            """
        ),
        {"city_id": city_id},
    )
    results = []
    for row in rows:
        d = dict(row._mapping)
        d["aqi_category"] = aqi_category(d["aqi"]) if d.get("aqi") is not None else None
        results.append(d)
    return results


async def get_readings_for_station(
    db: AsyncSession,
    station_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = 1,
    limit: int = 100,
) -> tuple[list[dict], int]:
    offset = (page - 1) * limit
    where_clauses = ["station_id = :station_id"]
    params: dict = {"station_id": station_id, "limit": limit, "offset": offset}
    if since:
        where_clauses.append("ts >= :since")
        params["since"] = since
    if until:
        where_clauses.append("ts <= :until")
        params["until"] = until
    where = " AND ".join(where_clauses)

    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM station_readings WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_row.scalar_one()

    rows = await db.execute(
        text(
            f"SELECT id, station_id, ts, pm25, pm10, no2, so2, co, o3, aqi, is_stale "
            f"FROM station_readings WHERE {where} ORDER BY ts DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    readings = [dict(r._mapping) for r in rows]
    for r in readings:
        r["aqi_category"] = aqi_category(r["aqi"]) if r.get("aqi") is not None else None
    return readings, total


# ── Weather ───────────────────────────────────────────────────────────────────


async def bulk_insert_weather(db: AsyncSession, readings: list[dict]) -> int:
    if not readings:
        return 0
    for r in readings:
        await db.execute(
            text(
                """
                INSERT INTO weather_readings
                    (id, city_id, ts, wind_speed, wind_dir, humidity, temp, pressure)
                VALUES
                    (:id, :city_id, :ts, :wind_speed, :wind_dir, :humidity, :temp, :pressure)
                ON CONFLICT DO NOTHING
                """
            ),
            {"id": str(uuid.uuid4()), **r},
        )
    await db.commit()
    return len(readings)


async def get_latest_weather(db: AsyncSession, city_id: str) -> dict | None:
    row = await db.execute(
        text(
            """
            SELECT id, city_id, ts, wind_speed, wind_dir, humidity, temp, pressure
            FROM weather_readings WHERE city_id = :city_id ORDER BY ts DESC LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    r = row.first()
    return dict(r._mapping) if r else None


# ── Fire Hotspots ─────────────────────────────────────────────────────────────


async def insert_fire_hotspot(
    db: AsyncSession,
    *,
    city_id: str,
    detected_at: datetime,
    geometry: dict,
    confidence: float,
    source: str = "NASA_FIRMS",
    frp: float | None = None,
) -> dict:
    hotspot_id = str(uuid.uuid4())
    await db.execute(
        text(
            """
            INSERT INTO fire_hotspots
                (id, city_id, detected_at, geometry, confidence, source, frp, created_at)
            VALUES
                (:id, :city_id, :detected_at, ST_GeomFromGeoJSON(:geom),
                 :confidence, :source, :frp, NOW())
            """
        ),
        {
            "id": hotspot_id,
            "city_id": city_id,
            "detected_at": detected_at,
            "geom": json.dumps(geometry),
            "confidence": confidence,
            "source": source,
            "frp": frp,
        },
    )
    await db.commit()
    return {"id": hotspot_id}


async def get_fire_hotspots_with_coords(
    db: AsyncSession, city_id: str, hours_back: int = 24
) -> list[dict]:
    """Return fire hotspots as flat dicts with lat/lon extracted from PostGIS geometry."""
    rows = await db.execute(
        text(
            """
            SELECT id, detected_at,
                   ST_Y(geometry::geometry) AS lat,
                   ST_X(geometry::geometry) AS lon,
                   confidence, frp, source
            FROM fire_hotspots
            WHERE city_id = :city_id
              AND detected_at > NOW() - INTERVAL '1 hour' * :hours_back
            ORDER BY detected_at DESC
            LIMIT 200
            """
        ),
        {"city_id": city_id, "hours_back": hours_back},
    )
    return [dict(r._mapping) for r in rows]


async def get_fire_hotspots(
    db: AsyncSession, city_id: str, since: datetime | None = None
) -> list[dict]:
    where = "city_id = :city_id"
    params: dict = {"city_id": city_id}
    if since:
        where += " AND detected_at >= :since"
        params["since"] = since
    rows = await db.execute(
        text(
            f"SELECT id, city_id, detected_at, "
            f"ST_AsGeoJSON(geometry) AS geometry, confidence, source, frp "
            f"FROM fire_hotspots WHERE {where} ORDER BY detected_at DESC LIMIT 200"
        ),
        params,
    )
    results = []
    for row in rows:
        d = dict(row._mapping)
        if d.get("geometry"):
            try:
                d["geometry"] = json.loads(d["geometry"])
            except (json.JSONDecodeError, ValueError):
                d["geometry"] = None
        results.append(d)
    return results


# ── Emission Sources ──────────────────────────────────────────────────────────


async def get_emission_sources(
    db: AsyncSession, city_id: str, page: int, limit: int
) -> tuple[list[dict], int]:
    offset = (page - 1) * limit
    count_row = await db.execute(
        text("SELECT COUNT(*) FROM emission_sources WHERE city_id = :city_id"),
        {"city_id": city_id},
    )
    total = count_row.scalar_one()
    rows = await db.execute(
        text(
            """
            SELECT id, city_id, name, type,
                   ST_AsGeoJSON(geometry) AS geometry,
                   permit_status, last_inspected_at, created_at
            FROM emission_sources WHERE city_id = :city_id
            ORDER BY name LIMIT :limit OFFSET :offset
            """
        ),
        {"city_id": city_id, "limit": limit, "offset": offset},
    )
    sources = []
    for row in rows:
        d = dict(row._mapping)
        if d.get("geometry"):
            try:
                d["geometry"] = json.loads(d["geometry"])
            except (json.JSONDecodeError, ValueError):
                d["geometry"] = None
        sources.append(d)
    return sources, total


async def create_emission_source(
    db: AsyncSession,
    *,
    city_id: str,
    name: str,
    type: str,
    geometry: dict | None,
    permit_status: str,
) -> dict:
    source_id = str(uuid.uuid4())
    if geometry:
        await db.execute(
            text(
                """
                INSERT INTO emission_sources
                    (id, city_id, name, type, geometry, permit_status, created_at, updated_at)
                VALUES
                    (:id, :city_id, :name, :type, ST_GeomFromGeoJSON(:geom), :permit_status,
                     NOW(), NOW())
                """
            ),
            {
                "id": source_id,
                "city_id": city_id,
                "name": name,
                "type": type,
                "geom": json.dumps(geometry),
                "permit_status": permit_status,
            },
        )
    else:
        await db.execute(
            text(
                """
                INSERT INTO emission_sources
                    (id, city_id, name, type, permit_status, created_at, updated_at)
                VALUES
                    (:id, :city_id, :name, :type, :permit_status, NOW(), NOW())
                """
            ),
            {
                "id": source_id,
                "city_id": city_id,
                "name": name,
                "type": type,
                "permit_status": permit_status,
            },
        )
    await db.commit()

    row = await db.execute(
        text(
            """
            SELECT id, city_id, name, type, ST_AsGeoJSON(geometry) AS geometry,
                   permit_status, last_inspected_at, created_at
            FROM emission_sources WHERE id = :id
            """
        ),
        {"id": source_id},
    )
    r = row.first()
    d = dict(r._mapping)
    if d.get("geometry"):
        try:
            d["geometry"] = json.loads(d["geometry"])
        except (json.JSONDecodeError, ValueError):
            d["geometry"] = None
    return d
