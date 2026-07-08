"""
Seed the database on first boot. Idempotent — skips rows that already exist.
Seeds:
  - sysadmin user (Module 00/01)
  - Delhi pilot city + 2 wards + 2 CAAQMS stations (Module 02)
  - 7 days of hourly station readings + emission sources (Module 03)
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Stable IDs so seeds are idempotent across restarts
DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
WARD_CP_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
WARD_DWARKA_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
STATION_AV_ID = "d4e5f6a7-b8c9-0123-def0-123456789013"
STATION_ITO_ID = "e5f6a7b8-c9d0-1234-ef01-234567890124"

# Approximate ward polygons (WGS84 — simplified for demo purposes)
# Connaught Place / Central Delhi ward
WARD_CP_GEOJSON = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [77.1900, 28.6200],
                [77.2400, 28.6200],
                [77.2400, 28.6450],
                [77.1900, 28.6450],
                [77.1900, 28.6200],
            ]
        ]
    ],
}

# Dwarka (West Delhi) ward
WARD_DWARKA_GEOJSON = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [77.0000, 28.5500],
                [77.0900, 28.5500],
                [77.0900, 28.6200],
                [77.0000, 28.6200],
                [77.0000, 28.5500],
            ]
        ]
    ],
}

# Real CAAQMS station locations (DPCC network)
STATION_AV_GEOJSON = {"type": "Point", "coordinates": [77.3154, 28.6469]}  # Anand Vihar
STATION_ITO_GEOJSON = {"type": "Point", "coordinates": [77.2403, 28.6273]}  # ITO


async def seed_admin() -> None:
    try:
        await _do_seed()
    except Exception as exc:
        logger.warning("Seed skipped (DB not ready yet)", error=str(exc))


async def _do_seed() -> None:
    async with AsyncSessionLocal() as session:
        await _seed_sysadmin(session)
        await _seed_delhi(session)
        await _seed_ingestion_data(session)
        await _seed_attribution_alerts(session)
        await _seed_enforcement_queue(session)
        await _seed_advisories(session)


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


async def _seed_delhi(session) -> None:
    # City
    exists = await session.execute(
        text("SELECT id FROM cities WHERE id = :id"), {"id": DELHI_CITY_ID}
    )
    if exists.fetchone():
        logger.info("Delhi seed already present, skipping")
        return

    await session.execute(
        text(
            """
            INSERT INTO cities (id, name, state, timezone, config_json, created_at, updated_at)
            VALUES (:id, 'Delhi', 'Delhi', 'Asia/Kolkata', '{}', NOW(), NOW())
            """
        ),
        {"id": DELHI_CITY_ID},
    )

    # Wards
    await session.execute(
        text(
            """
            INSERT INTO wards
                (id, city_id, name, geometry, population,
                 vulnerable_site_flags, created_at, updated_at)
            VALUES
                (:id, :city_id, :name, ST_GeomFromGeoJSON(:geom), :pop,
                 CAST(:flags AS jsonb), NOW(), NOW())
            """
        ),
        {
            "id": WARD_CP_ID,
            "city_id": DELHI_CITY_ID,
            "name": "Connaught Place",
            "geom": json.dumps(WARD_CP_GEOJSON),
            "pop": 350000,
            "flags": json.dumps({"schools": True, "hospitals": True}),
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO wards
                (id, city_id, name, geometry, population,
                 vulnerable_site_flags, created_at, updated_at)
            VALUES
                (:id, :city_id, :name, ST_GeomFromGeoJSON(:geom), :pop,
                 CAST(:flags AS jsonb), NOW(), NOW())
            """
        ),
        {
            "id": WARD_DWARKA_ID,
            "city_id": DELHI_CITY_ID,
            "name": "Dwarka",
            "geom": json.dumps(WARD_DWARKA_GEOJSON),
            "pop": 1200000,
            "flags": json.dumps({"schools": True, "hospitals": False}),
        },
    )

    # Stations
    await session.execute(
        text(
            """
            INSERT INTO stations
                (id, city_id, ward_id, external_station_code, name,
                 geometry, is_active, created_at, updated_at)
            VALUES
                (:id, :city_id, :ward_id, :code, :name,
                 ST_GeomFromGeoJSON(:geom), true, NOW(), NOW())
            """
        ),
        {
            "id": STATION_AV_ID,
            "city_id": DELHI_CITY_ID,
            "ward_id": None,
            "code": "DPCC_ANAND_VIHAR",
            "name": "Anand Vihar",
            "geom": json.dumps(STATION_AV_GEOJSON),
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO stations
                (id, city_id, ward_id, external_station_code, name,
                 geometry, is_active, created_at, updated_at)
            VALUES
                (:id, :city_id, :ward_id, :code, :name,
                 ST_GeomFromGeoJSON(:geom), true, NOW(), NOW())
            """
        ),
        {
            "id": STATION_ITO_ID,
            "city_id": DELHI_CITY_ID,
            "ward_id": WARD_CP_ID,
            "code": "DPCC_ITO",
            "name": "ITO",
            "geom": json.dumps(STATION_ITO_GEOJSON),
        },
    )

    await session.commit()
    logger.info("Delhi pilot city seeded", city_id=DELHI_CITY_ID, wards=2, stations=2)


async def _seed_ingestion_data(session) -> None:
    """Seed 7 days of hourly station readings + known Delhi emission sources."""
    import math
    import random

    # ── Emission sources ──────────────────────────────────────────────────────
    exists = await session.execute(
        text("SELECT id FROM emission_sources WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        logger.info("Ingestion seed already present, skipping")
        return

    emission_sources = [
        {
            "id": "f1a2b3c4-d5e6-7890-abcd-ef1234567801",
            "name": "Anand Vihar Bus Depot",
            "type": "vehicular",
            "geom": {"type": "Point", "coordinates": [77.3120, 28.6450]},
            "permit_status": "active",
        },
        {
            "id": "f2a2b3c4-d5e6-7890-abcd-ef1234567802",
            "name": "Delhi Thermal Power Station",
            "type": "industrial",
            "geom": {"type": "Point", "coordinates": [77.2800, 28.6200]},
            "permit_status": "active",
        },
        {
            "id": "f3a2b3c4-d5e6-7890-abcd-ef1234567803",
            "name": "Ashram Chowk Construction Site",
            "type": "construction",
            "geom": {"type": "Point", "coordinates": [77.2490, 28.5700]},
            "permit_status": "pending",
        },
        {
            "id": "f4a2b3c4-d5e6-7890-abcd-ef1234567804",
            "name": "Haryana Border Stubble Burning Zone",
            "type": "agricultural",
            "geom": {"type": "Point", "coordinates": [76.9500, 28.7500]},
            "permit_status": "expired",
        },
    ]
    for src in emission_sources:
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
                "geom": json.dumps(src["geom"]),
                "permit_status": src["permit_status"],
            },
        )

    # ── Historical station readings (7 days, hourly) ──────────────────────────
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=7)

    def make_reading(station_id: str, ts: datetime) -> dict:
        hour = ts.hour
        diurnal = 1.0 + 0.4 * (
            math.exp(-0.5 * ((hour - 8) / 2) ** 2) + math.exp(-0.5 * ((hour - 20) / 2) ** 2)
        )
        base_pm25 = 120.0 * diurnal
        pm25 = round(max(5.0, base_pm25 * random.uniform(0.85, 1.15)), 2)
        pm10 = round(pm25 * random.uniform(1.5, 2.2), 2)
        no2 = round(random.uniform(20, 90), 2)
        so2 = round(random.uniform(5, 30), 2)
        co = round(random.uniform(0.5, 3.0), 2)
        o3 = round(random.uniform(10, 60), 2)
        # Simple CPCB PM2.5 AQI
        bp = [
            (0, 30, 0, 50),
            (30, 60, 51, 100),
            (60, 90, 101, 200),
            (90, 120, 201, 300),
            (120, 250, 301, 400),
            (250, 500, 401, 500),
        ]
        aqi = 500
        for c_lo, c_hi, i_lo, i_hi in bp:
            if c_lo <= pm25 <= c_hi:
                aqi = round(i_lo + (i_hi - i_lo) * (pm25 - c_lo) / (c_hi - c_lo))
                break
        return {
            "id": str(uuid.uuid4()),
            "station_id": station_id,
            "ts": ts,
            "pm25": pm25,
            "pm10": pm10,
            "no2": no2,
            "so2": so2,
            "co": co,
            "o3": o3,
            "aqi": aqi,
        }

    station_ids = [STATION_AV_ID, STATION_ITO_ID]
    batch = []
    current = start
    while current <= now:
        for sid in station_ids:
            batch.append(make_reading(sid, current))
        current += timedelta(hours=1)
        # Flush every 200 rows to avoid huge transactions
        if len(batch) >= 200:
            for r in batch:
                await session.execute(
                    text(
                        "INSERT INTO station_readings"
                        " (id, station_id, ts, pm25, pm10, no2, so2, co, o3, aqi, is_stale)"
                        " VALUES"
                        " (:id, :station_id, :ts, :pm25, :pm10, :no2, :so2, :co, :o3, :aqi, false)"
                        " ON CONFLICT DO NOTHING"
                    ),
                    r,
                )
            await session.commit()
            batch = []

    for r in batch:
        await session.execute(
            text(
                "INSERT INTO station_readings"
                " (id, station_id, ts, pm25, pm10, no2, so2, co, o3, aqi, is_stale)"
                " VALUES"
                " (:id, :station_id, :ts, :pm25, :pm10, :no2, :so2, :co, :o3, :aqi, false)"
                " ON CONFLICT DO NOTHING"
            ),
            r,
        )
    await session.commit()

    total_readings = (7 * 24) * len(station_ids)
    logger.info(
        "Ingestion seed complete",
        emission_sources=len(emission_sources),
        station_readings=total_readings,
    )


async def _seed_attribution_alerts(session) -> None:
    """Seed a few test AQI alerts for Delhi (Module 04)."""
    exists = await session.execute(
        text("SELECT id FROM aqi_alerts WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        logger.info("Attribution alerts seed already present, skipping")
        return

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    alerts = [
        # A resolved "poor" alert from 3 days ago
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
        # A resolved "very_poor" alert from 1 day ago
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
        # An active "poor" alert right now
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
    logger.info("Attribution alerts seeded", count=len(alerts))


async def _seed_enforcement_queue(session) -> None:
    """Seed initial enforcement queue for Delhi (Module 06)."""
    exists = await session.execute(
        text("SELECT id FROM enforcement_queue WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        logger.info("Enforcement queue seed already present, skipping")
        return

    emission_source_ids = [
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

    for src_id, src_type, permit_status, src_name in emission_source_ids:
        attr_w = source_attr.get(src_type, 0.1)
        fc_w = 0.40  # moderate default forecast severity (AQI ~200)
        permit_w = permit_weights.get(permit_status, 0.5)
        days_w = 1.0  # never inspected
        score = round(0.35 * attr_w + 0.30 * fc_w + 0.20 * permit_w + 0.15 * days_w, 4)

        brief = (
            f"{src_name} ({src_type}) has been assigned a priority score of {score:.2f}/1.00. "
            f"This source accounts for approximately {attr_w * 100:.0f}% of current city "
            f"pollution attribution; the 24-hour peak forecast AQI is 200. "
            f"The permit is {permit_status} and the site has never been inspected."
        )

        await session.execute(
            text(
                """
                INSERT INTO enforcement_queue
                    (id, city_id, emission_source_id, priority_score,
                     evidence_brief_text, status, created_at, updated_at)
                VALUES
                    (:id, :city_id, :src_id, :score,
                     :brief, 'pending', NOW(), NOW())
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
    logger.info("Enforcement queue seeded", city_id=DELHI_CITY_ID, items=len(emission_source_ids))


async def _seed_advisories(session) -> None:
    """Seed 2 sample advisories for Delhi (Module 07) — one English, one Hindi."""
    exists = await session.execute(
        text("SELECT id FROM advisories WHERE city_id = :city_id LIMIT 1"),
        {"city_id": DELHI_CITY_ID},
    )
    if exists.fetchone():
        logger.info("Advisories seed already present, skipping")
        return

    advisories = [
        {
            "id": str(uuid.uuid4()),
            "language": "en",
            "title": "Air Quality Advisory — Poor Air Quality Warning",
            "body": (
                "Current AQI is 245 (Poor), primarily driven by vehicular emissions "
                "(vehicles and transport). Air quality is poor and likely to cause breathing "
                "discomfort to most people. Avoid prolonged outdoor physical activity — "
                "particularly jogging, cycling, or sports. Wear an N95/FFP2 mask if outdoor "
                "exposure is unavoidable. People with respiratory or cardiovascular conditions "
                "should stay indoors."
            ),
            "aqi_level": "Poor",
            "dominant_source": "vehicular",
        },
        {
            "id": str(uuid.uuid4()),
            "language": "hi",
            "title": "वायु गुणवत्ता सलाह — खराब वायु गुणवत्ता चेतावनी",
            "body": (
                "वर्तमान AQI 245 (Poor) है, जो मुख्यतः वाहनों के धुएं के कारण है। "
                "वायु गुणवत्ता खराब है और अधिकांश लोगों को सांस लेने में परेशानी हो सकती है। "
                "लंबे समय तक बाहर शारीरिक गतिविधि से बचें। "
                "यदि बाहर जाना अपरिहार्य हो तो N95/FFP2 मास्क पहनें। "
                "श्वसन या हृदय रोग से पीड़ित लोग घर के अंदर रहें।"
            ),
            "aqi_level": "Poor",
            "dominant_source": "vehicular",
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
                    (:id, :city_id, NULL, :language, :title, :body,
                     :aqi_level, :dominant_source, 'web', NULL, NOW())
                """
            ),
            {
                "id": adv["id"],
                "city_id": DELHI_CITY_ID,
                "language": adv["language"],
                "title": adv["title"],
                "body": adv["body"],
                "aqi_level": adv["aqi_level"],
                "dominant_source": adv["dominant_source"],
            },
        )

    await session.commit()
    logger.info("Advisories seeded", city_id=DELHI_CITY_ID, count=len(advisories))
