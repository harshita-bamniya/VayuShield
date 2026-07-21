"""City/Ward/Station service layer — business logic for Module 02."""

import json
import math

from sqlalchemy import text
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

# Known CAAQMS stations per city — used for nearest-station auto-assignment
_CITY_STATIONS: dict[str, list[dict]] = {
    "Delhi": [
        {"name": "Anand Vihar", "code": "DPCC_ANAND_VIHAR", "lat": 28.6469, "lon": 77.3154},
        {"name": "ITO", "code": "DPCC_ITO", "lat": 28.6273, "lon": 77.2403},
        {"name": "RK Puram", "code": "DPCC_RK_PURAM", "lat": 28.5651, "lon": 77.1762},
        {"name": "Punjabi Bagh", "code": "DPCC_PUNJABI_BAGH", "lat": 28.6712, "lon": 77.1314},
        {"name": "Dwarka Sector 8", "code": "DPCC_DWARKA_SEC8", "lat": 28.5921, "lon": 77.0460},
        {"name": "Rohini", "code": "DPCC_ROHINI", "lat": 28.7384, "lon": 77.1170},
        {"name": "Okhla Phase 2", "code": "DPCC_OKHLA_PH2", "lat": 28.5325, "lon": 77.2735},
        {"name": "Pusa IITM", "code": "IITM_PUSA", "lat": 28.6388, "lon": 77.1488},
        {"name": "Mandir Marg", "code": "DPCC_MANDIR_MARG", "lat": 28.6400, "lon": 77.2000},
        {"name": "Shadipur", "code": "DPCC_SHADIPUR", "lat": 28.6516, "lon": 77.1500},
        {"name": "Narela", "code": "DPCC_NARELA", "lat": 28.8543, "lon": 77.0922},
        {"name": "Bawana", "code": "DPCC_BAWANA", "lat": 28.7872, "lon": 77.0332},
        {"name": "Mundka", "code": "DPCC_MUNDKA", "lat": 28.6802, "lon": 77.0268},
        {"name": "Patparganj", "code": "DPCC_PATPARGANJ", "lat": 28.6215, "lon": 77.3015},
        {"name": "Sonia Vihar", "code": "DPCC_SONIA_VIHAR", "lat": 28.7132, "lon": 77.2756},
        {"name": "Vivek Vihar", "code": "DPCC_VIVEK_VIHAR", "lat": 28.6716, "lon": 77.3153},
    ],
    "Mumbai": [
        {"name": "Colaba", "code": "MPCB_COLABA", "lat": 18.9067, "lon": 72.8147},
        {"name": "Mazgaon", "code": "MPCB_MAZGAON", "lat": 18.9635, "lon": 72.8414},
        {"name": "Worli", "code": "MPCB_WORLI", "lat": 19.0048, "lon": 72.8172},
        {"name": "Chembur", "code": "MPCB_CHEMBUR", "lat": 19.0633, "lon": 72.9005},
        {"name": "Bandra", "code": "MPCB_BANDRA", "lat": 19.0522, "lon": 72.8414},
        {"name": "Kurla", "code": "MPCB_KURLA", "lat": 19.0726, "lon": 72.8845},
        {"name": "Powai", "code": "MPCB_POWAI", "lat": 19.1197, "lon": 72.9051},
        {"name": "Andheri", "code": "MPCB_ANDHERI", "lat": 19.1136, "lon": 72.8697},
        {"name": "Malad", "code": "MPCB_MALAD", "lat": 19.1874, "lon": 72.8484},
        {"name": "Borivali", "code": "MPCB_BORIVALI", "lat": 19.2347, "lon": 72.8567},
        {"name": "Mulund", "code": "MPCB_MULUND", "lat": 19.1726, "lon": 72.9560},
    ],
    "Bengaluru": [
        {"name": "BTM Layout", "code": "KSPCB_BTM", "lat": 12.9166, "lon": 77.6101},
        {"name": "Silk Board", "code": "KSPCB_SILK_BOARD", "lat": 12.9176, "lon": 77.6233},
        {"name": "Hebbal", "code": "KSPCB_HEBBAL", "lat": 13.0358, "lon": 77.5970},
        {"name": "Peenya", "code": "KSPCB_PEENYA", "lat": 13.0284, "lon": 77.5192},
        {"name": "City Railway Stn", "code": "KSPCB_CITY_RAILWAY", "lat": 12.9774, "lon": 77.5707},
        {"name": "Bapuji Nagar", "code": "KSPCB_BAPUJI_NAGAR", "lat": 12.9542, "lon": 77.5476},
    ],
    "Hyderabad": [
        {"name": "Sanathnagar", "code": "TSPCB_SANATHNAGAR", "lat": 17.4490, "lon": 78.4400},
        {"name": "Bollaram", "code": "TSPCB_BOLLARAM", "lat": 17.5244, "lon": 78.3826},
        {"name": "Zoo Park", "code": "TSPCB_ZOO_PARK", "lat": 17.3491, "lon": 78.4511},
        {"name": "Somajiguda", "code": "TSPCB_SOMAJIGUDA", "lat": 17.4239, "lon": 78.4738},
        {"name": "Nacharam", "code": "TSPCB_NACHARAM", "lat": 17.4014, "lon": 78.5508},
    ],
    "Chennai": [
        {"name": "Alandur", "code": "TNPCB_ALANDUR", "lat": 13.0002, "lon": 80.2042},
        {"name": "Manali", "code": "TNPCB_MANALI", "lat": 13.1673, "lon": 80.2618},
        {"name": "Velachery", "code": "TNPCB_VELACHERY", "lat": 12.9815, "lon": 80.2180},
        {"name": "Kodungaiyur", "code": "TNPCB_KODUNGAIYUR", "lat": 13.1367, "lon": 80.2567},
    ],
    "Kolkata": [
        {
            "name": "Rabindra Bharati",
            "code": "WBPCB_RABINDRA_BHARATI",
            "lat": 22.5962,
            "lon": 88.3674,
        },
        {"name": "Ballygunge", "code": "WBPCB_BALLYGUNGE", "lat": 22.5264, "lon": 88.3671},
        {"name": "Jadavpur", "code": "WBPCB_JADAVPUR", "lat": 22.4967, "lon": 88.3713},
        {"name": "Fort William", "code": "WBPCB_FORT_WILLIAM", "lat": 22.5568, "lon": 88.3377},
    ],
    "Pune": [
        {"name": "Shivajinagar", "code": "MPCB_SHIVAJINAGAR", "lat": 18.5308, "lon": 73.8475},
        {"name": "Katraj", "code": "MPCB_KATRAJ", "lat": 18.4564, "lon": 73.8684},
        {"name": "Pashan", "code": "MPCB_PASHAN", "lat": 18.5362, "lon": 73.7943},
        {"name": "Hadapsar", "code": "MPCB_HADAPSAR", "lat": 18.5089, "lon": 73.9259},
    ],
    "Lucknow": [
        {"name": "Talkatora", "code": "UPPCB_TALKATORA", "lat": 26.8558, "lon": 80.9164},
        {"name": "Lalbagh", "code": "UPPCB_LALBAGH", "lat": 26.8536, "lon": 80.9271},
        {"name": "Gomti Nagar", "code": "UPPCB_GOMTI_NAGAR", "lat": 26.8562, "lon": 81.0008},
    ],
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _geojson_centroid(geometry: dict | None) -> tuple[float, float] | None:
    """Return (lat, lon) centroid of a GeoJSON Polygon or MultiPolygon. Returns None on failure."""
    if not geometry:
        return None
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    try:
        if gtype == "Point":
            return float(coords[1]), float(coords[0])
        if gtype == "Polygon" and coords:
            ring = coords[0]
            return sum(c[1] for c in ring) / len(ring), sum(c[0] for c in ring) / len(ring)
        if gtype == "MultiPolygon" and coords:
            ring = coords[0][0]
            return sum(c[1] for c in ring) / len(ring), sum(c[0] for c in ring) / len(ring)
    except (IndexError, TypeError, ZeroDivisionError):
        pass
    return None


async def _auto_assign_station_for_ward(
    db: AsyncSession,
    city_id: str,
    city_name: str,
    ward_id: str,
    geometry: dict | None,
) -> None:
    """Find the nearest known CAAQMS station and assign it to the ward."""
    from app.core.logging import logger

    stations = _CITY_STATIONS.get(city_name, [])
    if not stations:
        return

    centroid = _geojson_centroid(geometry)
    if not centroid:
        logger.warning("Cannot auto-assign station: ward has no geometry", ward_id=ward_id)
        return

    ward_lat, ward_lon = centroid
    nearest = min(stations, key=lambda s: _haversine(ward_lat, ward_lon, s["lat"], s["lon"]))
    dist_km = _haversine(ward_lat, ward_lon, nearest["lat"], nearest["lon"])

    existing = await db.execute(
        text(
            "SELECT id, ward_id FROM stations"
            " WHERE city_id = :cid AND external_station_code = :code"
        ),
        {"cid": city_id, "code": nearest["code"]},
    )
    row = existing.fetchone()

    if row:
        if row[1] is None:
            await db.execute(
                text("UPDATE stations SET ward_id = :wid, updated_at = NOW() WHERE id = :id"),
                {"wid": ward_id, "id": row[0]},
            )
            await db.commit()
            logger.info(
                "Auto-assigned existing station to ward",
                station=nearest["name"],
                ward_id=ward_id,
                dist_km=round(dist_km, 1),
            )
    else:
        await repo.create_station(
            db,
            city_id=city_id,
            ward_id=ward_id,
            external_station_code=nearest["code"],
            name=nearest["name"],
            geometry={"type": "Point", "coordinates": [nearest["lon"], nearest["lat"]]},
            is_active=True,
        )
        logger.info(
            "Auto-created and assigned nearest station to ward",
            station=nearest["name"],
            ward_id=ward_id,
            dist_km=round(dist_km, 1),
        )


async def compute_vulnerability_scores(db: AsyncSession, city_id: str) -> None:
    """Compute a 0–1 vulnerability score for every ward and persist it in vulnerable_site_flags.

    Score = population_norm × 0.4 + aqi_norm × 0.6
    Tiers: Critical ≥0.75 · High ≥0.5 · Moderate ≥0.25 · Low <0.25
    """
    from app.core.logging import logger

    rows = await db.execute(
        text("""
            WITH ward_aqi AS (
                SELECT s.ward_id, AVG(sr.aqi) AS avg_aqi
                FROM (
                    SELECT DISTINCT ON (station_id) station_id, aqi
                    FROM station_readings
                    ORDER BY station_id, ts DESC
                ) sr
                JOIN stations s ON s.id = sr.station_id AND s.is_active = true
                WHERE s.city_id = :cid AND sr.aqi IS NOT NULL
                GROUP BY s.ward_id
            )
            SELECT w.id, w.population, w.vulnerable_site_flags, wa.avg_aqi
            FROM wards w
            LEFT JOIN ward_aqi wa ON wa.ward_id = w.id
            WHERE w.city_id = :cid
        """),
        {"cid": city_id},
    )
    ward_data = [dict(r._mapping) for r in rows]
    if not ward_data:
        return

    populations = [w["population"] for w in ward_data if w["population"]]
    max_pop = max(populations) if populations else 1

    for w in ward_data:
        pop_norm = (w["population"] or 0) / max_pop if max_pop > 0 else 0.0
        aqi_norm = min(float(w["avg_aqi"] or 0) / 500.0, 1.0)
        score = round(pop_norm * 0.4 + aqi_norm * 0.6, 3)
        tier = (
            "Critical"
            if score >= 0.75
            else "High"
            if score >= 0.5
            else "Moderate"
            if score >= 0.25
            else "Low"
        )
        flags = dict(w["vulnerable_site_flags"] or {})
        flags["vulnerability_score"] = score
        flags["vulnerability_tier"] = tier
        await db.execute(
            text(
                "UPDATE wards SET vulnerable_site_flags = CAST(:flags AS jsonb),"
                " updated_at = NOW() WHERE id = :id"
            ),
            {"id": w["id"], "flags": json.dumps(flags)},
        )

    await db.commit()
    logger.info("Vulnerability scores computed", city_id=city_id, wards=len(ward_data))


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

    await _auto_assign_station_for_ward(db, city_id, city.name, ward["id"], geometry)

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
