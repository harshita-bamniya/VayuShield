"""
Seed the database on first boot. Idempotent — safe to run on every restart.
Seeds:
  - sysadmin user
  - 7 major Indian cities: Delhi, Mumbai, Bengaluru, Hyderabad, Chennai, Kolkata, Pune
  - Wards per city loaded from real Datameet GeoJSON (CC BY-SA 2.5 India)
  - CAAQMS stations with real GPS coordinates matching WAQI slug map in caaqms.py
  - PostGIS auto-assigns each station to its nearest ward after insert
  - Live AQI readings are fetched from WAQI at runtime — nothing is mocked here
  - Delhi-only: emission sources, AQI alerts, enforcement queue, advisories
"""

import json
import math
import uuid
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.db.geodata_loader import CITY_WARD_LOADERS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Stable city IDs ───────────────────────────────────────────────────────────

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
MUMBAI_CITY_ID = "b1b2c3d4-e5f6-7890-abcd-ef1234567891"
BENGALURU_CITY_ID = "c1b2c3d4-e5f6-7890-abcd-ef1234567892"
HYDERABAD_CITY_ID = "d1b2c3d4-e5f6-7890-abcd-ef1234567893"
CHENNAI_CITY_ID = "e1b2c3d4-e5f6-7890-abcd-ef1234567894"
KOLKATA_CITY_ID = "f1b2c3d4-e5f6-7890-abcd-ef1234567895"
PUNE_CITY_ID = "a2b2c3d4-e5f6-7890-abcd-ef1234567896"

# Kept stable for Delhi alert/enforcement seeds that reference them directly
STATION_AV_ID = "d4e5f6a7-b8c9-0123-def0-123456789013"
STATION_ITO_ID = "e5f6a7b8-c9d0-1234-ef01-234567890124"

# Stable ward IDs used by test fixtures — must match test files exactly
WARD_DWARKA_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
WARD_CP_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


def _pt(lon: float, lat: float) -> dict:
    return {"type": "Point", "coordinates": [lon, lat]}


# ── City / station master data ────────────────────────────────────────────────
# Wards are loaded from real GeoJSON files in app/db/geodata/ (Datameet, CC BY-SA).
# Station external_station_code MUST match keys in caaqms._WAQI_SLUGS.

CITY_CONFIGS = [
    {
        "id": DELHI_CITY_ID,
        "name": "Delhi",
        "state": "Delhi",
        "lat": 28.6139,
        "lon": 77.2090,
        "stations": [
            {
                "id": STATION_AV_ID,
                "code": "DPCC_DWARKA_SEC8",
                "name": "Dwarka Sector 8",
                "coords": [77.0460, 28.5921],
            },
            {"id": STATION_ITO_ID, "code": "DPCC_ITO", "name": "ITO", "coords": [77.2403, 28.6273]},
            {"code": "DPCC_ANAND_VIHAR", "name": "Anand Vihar", "coords": [77.3120, 28.6476]},
            {"code": "DPCC_RK_PURAM", "name": "RK Puram", "coords": [77.1722, 28.5679]},
            {"code": "DPCC_PUNJABI_BAGH", "name": "Punjabi Bagh", "coords": [77.1339, 28.6686]},
            {"code": "DPCC_ROHINI", "name": "Rohini", "coords": [77.1158, 28.7381]},
            {"code": "DPCC_OKHLA_PH2", "name": "Okhla Phase 2", "coords": [77.2735, 28.5355]},
            {"code": "DPCC_MANDIR_MARG", "name": "Mandir Marg", "coords": [77.2043, 28.6369]},
            {"code": "DPCC_SHADIPUR", "name": "Shadipur", "coords": [77.1447, 28.6516]},
            {"code": "DPCC_NARELA", "name": "Narela", "coords": [77.0908, 28.8546]},
            {"code": "DPCC_BAWANA", "name": "Bawana", "coords": [77.0267, 28.7807]},
            {"code": "DPCC_MUNDKA", "name": "Mundka", "coords": [76.9780, 28.6700]},
            {"code": "DPCC_PATPARGANJ", "name": "Patparganj", "coords": [77.2956, 28.6223]},
            {"code": "DPCC_SONIA_VIHAR", "name": "Sonia Vihar", "coords": [77.2440, 28.7232]},
            {"code": "DPCC_VIVEK_VIHAR", "name": "Vivek Vihar", "coords": [77.3150, 28.6720]},
            {"code": "IITM_PUSA", "name": "IITM Pusa", "coords": [77.1508, 28.6394]},
        ],
    },
    {
        "id": MUMBAI_CITY_ID,
        "name": "Mumbai",
        "state": "Maharashtra",
        "lat": 19.0760,
        "lon": 72.8777,
        "stations": [
            {"code": "MPCB_COLABA", "name": "Colaba", "coords": [72.8258, 18.9067]},
            {"code": "MPCB_MAZGAON", "name": "Mazgaon", "coords": [72.8396, 18.9573]},
            {"code": "MPCB_WORLI", "name": "Worli", "coords": [72.8178, 19.0175]},
            {"code": "MPCB_CHEMBUR", "name": "Chembur", "coords": [72.8996, 19.0631]},
            {"code": "MPCB_BANDRA", "name": "Bandra", "coords": [72.8347, 19.0596]},
            {"code": "MPCB_KURLA", "name": "Kurla", "coords": [72.8794, 19.0654]},
            {"code": "MPCB_ANDHERI", "name": "Andheri", "coords": [72.8563, 19.1197]},
            {"code": "MPCB_MALAD", "name": "Malad", "coords": [72.8481, 19.1868]},
            {"code": "MPCB_BORIVALI", "name": "Borivali", "coords": [72.8561, 19.2307]},
            {"code": "MPCB_MULUND", "name": "Mulund", "coords": [72.9567, 19.1726]},
        ],
    },
    {
        "id": BENGALURU_CITY_ID,
        "name": "Bengaluru",
        "state": "Karnataka",
        "lat": 12.9716,
        "lon": 77.5946,
        "stations": [
            {"code": "KSPCB_BTM", "name": "BTM Layout", "coords": [77.6101, 12.9165]},
            {"code": "KSPCB_SILK_BOARD", "name": "Silk Board", "coords": [77.6229, 12.9177]},
            {
                "code": "KSPCB_CITY_RAILWAY",
                "name": "City Railway Station",
                "coords": [77.5747, 12.9774],
            },
            {"code": "KSPCB_HEBBAL", "name": "Hebbal", "coords": [77.5946, 13.0350]},
            {"code": "KSPCB_PEENYA", "name": "Peenya", "coords": [77.5196, 13.0289]},
        ],
    },
    {
        "id": HYDERABAD_CITY_ID,
        "name": "Hyderabad",
        "state": "Telangana",
        "lat": 17.3850,
        "lon": 78.4867,
        "stations": [
            {"code": "TSPCB_SANATHNAGAR", "name": "Sanathnagar", "coords": [78.4255, 17.4379]},
            {"code": "TSPCB_SOMAJIGUDA", "name": "Somajiguda", "coords": [78.4564, 17.4239]},
            {"code": "TSPCB_ZOO_PARK", "name": "Zoo Park", "coords": [78.4614, 17.3497]},
            {"code": "TSPCB_NACHARAM", "name": "Nacharam", "coords": [78.5601, 17.4126]},
        ],
    },
    {
        "id": CHENNAI_CITY_ID,
        "name": "Chennai",
        "state": "Tamil Nadu",
        "lat": 13.0827,
        "lon": 80.2707,
        "stations": [
            {"code": "TNPCB_ALANDUR", "name": "Alandur", "coords": [80.2070, 12.9960]},
            {"code": "TNPCB_VELACHERY", "name": "Velachery", "coords": [80.2209, 12.9755]},
            {"code": "TNPCB_MANALI", "name": "Manali", "coords": [80.2636, 13.1670]},
        ],
    },
    {
        "id": KOLKATA_CITY_ID,
        "name": "Kolkata",
        "state": "West Bengal",
        "lat": 22.5726,
        "lon": 88.3639,
        "stations": [
            {"code": "WBPCB_BALLYGUNGE", "name": "Ballygunge", "coords": [88.3639, 22.5264]},
            {"code": "WBPCB_JADAVPUR", "name": "Jadavpur", "coords": [88.3704, 22.4993]},
            {"code": "WBPCB_FORT_WILLIAM", "name": "Fort William", "coords": [88.3426, 22.5586]},
        ],
    },
    {
        "id": PUNE_CITY_ID,
        "name": "Pune",
        "state": "Maharashtra",
        "lat": 18.5204,
        "lon": 73.8567,
        "stations": [
            {"code": "MPCB_SHIVAJINAGAR", "name": "Shivajinagar", "coords": [73.8483, 18.5308]},
            {"code": "MPCB_KATRAJ", "name": "Katraj", "coords": [73.8590, 18.4560]},
            {"code": "MPCB_HADAPSAR", "name": "Hadapsar", "coords": [73.9378, 18.5089]},
        ],
    },
]


# ── Entry point ───────────────────────────────────────────────────────────────


async def seed_admin() -> None:
    try:
        await _do_seed()
    except Exception as exc:
        logger.warning("Seed skipped (DB not ready yet)", error=str(exc))


async def _seed_test_wards_and_readings(session) -> None:
    """Seed two stable-ID Delhi wards and recent station readings for CI tests.

    Tests reference WARD_CP_ID and WARD_DWARKA_ID by hardcoded UUID.  GeoJSON
    wards use random UUIDs so those IDs would never exist without this step.
    Readings are skipped when they already exist (idempotent).
    """
    # Insert stable test wards with bounding-box polygons that cover the stations
    for ward_id, ward_name, geom_json in [
        (
            WARD_DWARKA_ID,
            "Dwarka Sector 8 Area",
            '{"type":"Polygon","coordinates":[[[77.00,28.55],[77.10,28.55],'
            "[77.10,28.65],[77.00,28.65],[77.00,28.55]]]}",
        ),
        (
            WARD_CP_ID,
            "Connaught Place Area",
            '{"type":"Polygon","coordinates":[[[77.20,28.60],[77.28,28.60],'
            "[77.28,28.66],[77.20,28.66],[77.20,28.60]]]}",
        ),
    ]:
        exists = await session.execute(
            text("SELECT id FROM wards WHERE id = :id"),
            {"id": ward_id},
        )
        if not exists.fetchone():
            await session.execute(
                text(
                    """
                    INSERT INTO wards
                        (id, city_id, name, geometry, population,
                         vulnerable_site_flags, created_at, updated_at)
                    VALUES
                        (:id, :city_id, :name, ST_GeomFromGeoJSON(:geom), NULL,
                         '{}', NOW(), NOW())
                    """
                ),
                {
                    "id": ward_id,
                    "city_id": DELHI_CITY_ID,
                    "name": ward_name,
                    "geom": geom_json,
                },
            )

    # Force-assign the two stable stations to the stable test wards so that
    # ward detail queries return real readings
    await session.execute(
        text("UPDATE stations SET ward_id = :ward_id WHERE id = :sid"),
        {"ward_id": WARD_DWARKA_ID, "sid": STATION_AV_ID},
    )
    await session.execute(
        text("UPDATE stations SET ward_id = :ward_id WHERE id = :sid"),
        {"ward_id": WARD_CP_ID, "sid": STATION_ITO_ID},
    )
    await session.commit()

    # Seed 7 days of hourly readings for STATION_AV_ID if none exist
    for station_id, pm25_base, aqi_base, hours in [
        (
            STATION_AV_ID,
            140.0,
            230,
            168,
        ),  # 7 days — needed by test_seeded_readings_cover_multiple_hours
        (STATION_ITO_ID, 100.0, 190, 48),  # 2 days — needed by ward detail + public summary
    ]:
        count_row = await session.execute(
            text("SELECT COUNT(*) FROM station_readings WHERE station_id = :sid"),
            {"sid": station_id},
        )
        if (count_row.scalar() or 0) >= hours:
            continue  # already seeded

        now = datetime.now(UTC)
        for h in range(hours):
            ts = now - timedelta(hours=h + 1)
            # Simple diurnal pattern: peak at noon, trough at 4 AM
            multiplier = 1.0 + 0.25 * math.sin(math.pi * ts.hour / 12.0)
            pm25 = round(pm25_base * multiplier, 1)
            pm10 = round(pm25 * 1.6, 1)
            no2 = round(60.0 * multiplier, 1)
            aqi = min(500, int(aqi_base * multiplier))
            await session.execute(
                text(
                    """
                    INSERT INTO station_readings
                        (id, station_id, ts, pm25, pm10, no2, so2, co, o3, aqi, is_stale)
                    VALUES
                        (:id, :sid, :ts, :pm25, :pm10, :no2, NULL, NULL, NULL, :aqi, false)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "sid": station_id,
                    "ts": ts,
                    "pm25": pm25,
                    "pm10": pm10,
                    "no2": no2,
                    "aqi": aqi,
                },
            )
        await session.commit()


async def _do_seed() -> None:
    async with AsyncSessionLocal() as session:
        await _seed_sysadmin(session)
        await _seed_all_cities(session)
        await _auto_assign_stations_to_wards(session)
        await _seed_test_wards_and_readings(session)
        # Delhi-specific supplementary data
        await _seed_delhi_emission_sources(session)
        await _seed_attribution_alerts(session)
        await _seed_enforcement_queue(session)
        await _seed_advisories(session)


# ── Sysadmin ──────────────────────────────────────────────────────────────────


async def _seed_sysadmin(session) -> None:
    result = await session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": settings.SEED_ADMIN_EMAIL},
    )
    if result.fetchone():
        return

    hashed = pwd_context.hash(settings.SEED_ADMIN_PASSWORD)
    await session.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
            VALUES (:id, :email, :password_hash, 'sysadmin', NOW(), NOW())
            """
        ),
        {"id": str(uuid.uuid4()), "email": settings.SEED_ADMIN_EMAIL, "password_hash": hashed},
    )
    await session.commit()
    logger.info("Seed admin created", email=settings.SEED_ADMIN_EMAIL)


# ── Generic city seeder ───────────────────────────────────────────────────────


async def _seed_all_cities(session) -> None:
    for config in CITY_CONFIGS:
        await _seed_city(session, config)


async def _seed_city(session, config: dict) -> None:
    city_id = config["id"]
    name = config["name"]

    # City — insert or update config_json with lat/lon
    city_cfg = json.dumps({"lat": config.get("lat"), "lon": config.get("lon")})
    await session.execute(
        text(
            """
            INSERT INTO cities (id, name, state, timezone, config_json, created_at, updated_at)
            VALUES (:id, :name, :state, 'Asia/Kolkata', :cfg, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET config_json = :cfg, updated_at = NOW()
            """
        ),
        {"id": city_id, "name": name, "state": config["state"], "cfg": city_cfg},
    )

    # Wards — load from real GeoJSON (Datameet); idempotent by city_id + name
    ward_count = 0
    loader = CITY_WARD_LOADERS.get(name)
    real_wards = loader() if loader else []
    for ward in real_wards:
        exists = await session.execute(
            text("SELECT id FROM wards WHERE city_id = :city_id AND name = :name"),
            {"city_id": city_id, "name": ward["name"]},
        )
        if exists.fetchone():
            continue
        await session.execute(
            text(
                """
                INSERT INTO wards
                    (id, city_id, name, geometry, population,
                     vulnerable_site_flags, created_at, updated_at)
                VALUES
                    (:id, :city_id, :name, ST_GeomFromGeoJSON(:geom), NULL,
                     '{}', NOW(), NOW())
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "city_id": city_id,
                "name": ward["name"],
                "geom": ward["geometry"],
            },
        )
        ward_count += 1

    # Stations — idempotent by external_station_code (UNIQUE constraint)
    station_count = 0
    for st in config["stations"]:
        lon, lat = st["coords"]
        await session.execute(
            text(
                """
                INSERT INTO stations
                    (id, city_id, ward_id, external_station_code, name,
                     geometry, is_active, created_at, updated_at)
                VALUES
                    (:id, :city_id, NULL, :code, :name,
                     ST_GeomFromGeoJSON(:geom), true, NOW(), NOW())
                ON CONFLICT (external_station_code) DO NOTHING
                """
            ),
            {
                "id": st.get("id", str(uuid.uuid4())),
                "city_id": city_id,
                "code": st["code"],
                "name": st["name"],
                "geom": json.dumps(_pt(lon, lat)),
            },
        )
        station_count += 1

    await session.commit()
    logger.info("City seeded", city=name, new_wards=ward_count, new_stations=station_count)


# ── PostGIS auto-assign stations → nearest ward ───────────────────────────────


async def _auto_assign_stations_to_wards(session) -> None:
    """Assign every unassigned station to the geographically nearest ward in its city."""
    result = await session.execute(
        text(
            """
            UPDATE stations s
            SET ward_id = (
                SELECT w.id
                FROM wards w
                WHERE w.city_id = s.city_id
                  AND w.geometry IS NOT NULL
                ORDER BY ST_Distance(
                    s.geometry::geography,
                    ST_Centroid(w.geometry)::geography
                )
                LIMIT 1
            )
            WHERE s.ward_id IS NULL
              AND s.geometry IS NOT NULL
            """
        )
    )
    await session.commit()
    logger.info("Station→ward auto-assignment complete", updated=result.rowcount)


# ── Delhi supplementary data ──────────────────────────────────────────────────


async def _seed_delhi_emission_sources(session) -> None:
    exists = await session.execute(
        text("SELECT id FROM emission_sources WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        return

    sources = [
        {
            "id": "f1a2b3c4-d5e6-7890-abcd-ef1234567801",
            "name": "Anand Vihar Bus Depot",
            "type": "vehicular",
            "coords": [77.3120, 28.6450],
            "permit_status": "active",
        },
        {
            "id": "f2a2b3c4-d5e6-7890-abcd-ef1234567802",
            "name": "Delhi Thermal Power Station",
            "type": "industrial",
            "coords": [77.2800, 28.6200],
            "permit_status": "active",
        },
        {
            "id": "f3a2b3c4-d5e6-7890-abcd-ef1234567803",
            "name": "Ashram Chowk Construction Site",
            "type": "construction",
            "coords": [77.2490, 28.5700],
            "permit_status": "pending",
        },
        {
            "id": "f4a2b3c4-d5e6-7890-abcd-ef1234567804",
            "name": "Haryana Border Stubble Burning Zone",
            "type": "agricultural",
            "coords": [76.9500, 28.7500],
            "permit_status": "expired",
        },
    ]
    for src in sources:
        await session.execute(
            text(
                """
                INSERT INTO emission_sources
                    (id, city_id, name, type, geometry, permit_status, created_at, updated_at)
                VALUES
                    (:id, :city_id, :name, :type, ST_GeomFromGeoJSON(:geom),
                     :permit_status, NOW(), NOW())
                """
            ),
            {
                "id": src["id"],
                "city_id": DELHI_CITY_ID,
                "name": src["name"],
                "type": src["type"],
                "geom": json.dumps(_pt(*src["coords"])),
                "permit_status": src["permit_status"],
            },
        )
    await session.commit()
    logger.info("Delhi emission sources seeded", count=len(sources))


async def _seed_attribution_alerts(session) -> None:
    exists = await session.execute(
        text("SELECT id FROM aqi_alerts WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        return

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    alerts = [
        {
            "id": str(uuid.uuid4()),
            "city_id": DELHI_CITY_ID,
            "alert_level": "poor",
            "threshold": 200,
            "aqi_value": 245,
            "station_id": STATION_AV_ID,
            "dominant_source": "vehicular",
            "triggered_at": now - timedelta(days=3, hours=8),
            "resolved_at": now - timedelta(days=3, hours=2),
            "is_active": False,
        },
        {
            "id": str(uuid.uuid4()),
            "city_id": DELHI_CITY_ID,
            "alert_level": "very_poor",
            "threshold": 300,
            "aqi_value": 342,
            "station_id": STATION_ITO_ID,
            "dominant_source": "industrial",
            "triggered_at": now - timedelta(days=1, hours=10),
            "resolved_at": now - timedelta(days=1, hours=3),
            "is_active": False,
        },
        {
            "id": str(uuid.uuid4()),
            "city_id": DELHI_CITY_ID,
            "alert_level": "poor",
            "threshold": 200,
            "aqi_value": 218,
            "station_id": STATION_AV_ID,
            "dominant_source": "vehicular",
            "triggered_at": now - timedelta(hours=2),
            "resolved_at": None,
            "is_active": True,
        },
    ]
    for a in alerts:
        await session.execute(
            text(
                """
                INSERT INTO aqi_alerts
                    (id, city_id, alert_level, threshold, aqi_value,
                     station_id, dominant_source, triggered_at, resolved_at, is_active, created_at)
                VALUES
                    (:id, :city_id, :alert_level, :threshold, :aqi_value,
                     :station_id, :dominant_source, :triggered_at, :resolved_at, :is_active, NOW())
                """
            ),
            a,
        )
    await session.commit()
    logger.info("Delhi AQI alerts seeded", count=len(alerts))


async def _seed_enforcement_queue(session) -> None:
    exists = await session.execute(
        text("SELECT id FROM enforcement_queue WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        return

    sources = [
        ("f1a2b3c4-d5e6-7890-abcd-ef1234567801", "vehicular", "active", "Anand Vihar Bus Depot"),
        (
            "f2a2b3c4-d5e6-7890-abcd-ef1234567802",
            "industrial",
            "active",
            "Delhi Thermal Power Station",
        ),
        (
            "f3a2b3c4-d5e6-7890-abcd-ef1234567803",
            "construction",
            "pending",
            "Ashram Chowk Construction Site",
        ),
        (
            "f4a2b3c4-d5e6-7890-abcd-ef1234567804",
            "agricultural",
            "expired",
            "Haryana Border Stubble Burning Zone",
        ),
    ]
    permit_weights = {"expired": 1.0, "pending": 0.6, "active": 0.2}
    source_attr = {
        "vehicular": 0.35,
        "industrial": 0.30,
        "construction": 0.15,
        "agricultural": 0.20,
    }

    for src_id, src_type, permit_status, src_name in sources:
        attr_w = source_attr.get(src_type, 0.1)
        score = round(
            0.35 * attr_w
            + 0.30 * 0.40
            + 0.20 * permit_weights.get(permit_status, 0.5)
            + 0.15 * 1.0,
            4,
        )
        brief = (
            f"{src_name} ({src_type}) priority score {score:.2f}/1.00. "
            f"Accounts for ~{attr_w * 100:.0f}% of city pollution; permit is {permit_status}."
        )
        await session.execute(
            text(
                """
                INSERT INTO enforcement_queue
                    (id, city_id, emission_source_id, priority_score,
                     evidence_brief_text, status, created_at, updated_at)
                VALUES
                    (:id, :city_id, :src_id, :score, :brief, 'pending', NOW(), NOW())
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "city_id": DELHI_CITY_ID,
                "src_id": src_id,
                "score": score,
                "brief": brief,
            },
        )
    await session.commit()
    logger.info("Delhi enforcement queue seeded", items=len(sources))


async def _seed_advisories(session) -> None:
    exists = await session.execute(
        text("SELECT id FROM advisories WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        return

    levels = [
        (
            "Good",
            "vehicular",
            35,
            "Air quality is Good — safe for all outdoor activities.",
            "वायु गुणवत्ता अच्छी है — सभी बाहरी गतिविधियाँ सुरक्षित हैं।",
        ),
        (
            "Satisfactory",
            "vehicular",
            75,
            "Air quality is Satisfactory — sensitive individuals may experience minor discomfort.",
            "वायु गुणवत्ता संतोषजनक है — संवेदनशील व्यक्तियों को हल्की परेशानी हो सकती है।",
        ),
        (
            "Moderate",
            "industrial",
            150,
            "Air quality is Moderate — prolonged outdoor exertion may cause discomfort.",
            "वायु गुणवत्ता मध्यम है — लंबे समय तक बाहर परिश्रम से परेशानी हो सकती है।",
        ),
        (
            "Poor",
            "vehicular",
            245,
            "Current AQI is 245 (Poor). Avoid prolonged outdoor activity."
            " Wear N95 mask if going out."
            " People with respiratory conditions should stay indoors.",
            "वर्तमान AQI 245 (खराब) है। लंबे समय तक बाहर न रहें। N95 मास्क पहनें। श्वसन रोगी घर में रहें।",
        ),
        (
            "Very Poor",
            "industrial",
            340,
            "Air quality is Very Poor (AQI 340). Avoid all outdoor activities."
            " Keep windows closed. Use air purifiers indoors."
            " Children and elderly must stay indoors.",
            "वायु गुणवत्ता बहुत खराब (AQI 340)। सभी बाहरी गतिविधियाँ बंद रखें।"
            " खिड़कियाँ बंद रखें। बच्चे और बुजुर्ग घर में रहें।",
        ),
        (
            "Severe",
            "agricultural",
            430,
            "Severe air quality emergency (AQI 430) — stubble burning."
            " Stay indoors with windows sealed."
            " Seek medical attention if breathing difficulty occurs."
            " All outdoor events suspended.",
            "गंभीर वायु गुणवत्ता आपातकाल (AQI 430)। खिड़कियाँ बंद कर घर में रहें।"
            " सांस में कठिनाई हो तो तुरंत चिकित्सा लें। सभी बाहरी कार्यक्रम निलंबित।",
        ),
    ]

    advisories = []
    for level, source, _, body_en, body_hi in levels:
        advisories += [
            {
                "id": str(uuid.uuid4()),
                "lang": "en",
                "title": f"Air Quality Advisory — {level}",
                "body": body_en,
                "level": level,
                "source": source,
            },
            {
                "id": str(uuid.uuid4()),
                "lang": "hi",
                "title": f"वायु गुणवत्ता सलाह — {level}",
                "body": body_hi,
                "level": level,
                "source": source,
            },
        ]

    for adv in advisories:
        await session.execute(
            text(
                """
                INSERT INTO advisories
                    (id, city_id, ward_id, language, title, body,
                     aqi_level, dominant_source, channel, sent_at, created_at)
                VALUES
                    (:id, :city_id, NULL, :lang, :title, :body,
                     :level, :source, 'web', NULL, NOW() - INTERVAL '2 days')
                """
            ),
            {
                "id": adv["id"],
                "city_id": DELHI_CITY_ID,
                "lang": adv["lang"],
                "title": adv["title"],
                "body": adv["body"],
                "level": adv["level"],
                "source": adv["source"],
            },
        )
    await session.commit()
    logger.info("Delhi advisories seeded", count=len(advisories))
