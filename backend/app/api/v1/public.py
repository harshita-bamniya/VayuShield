"""Public advisory API — no authentication required."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["public"])


@router.get("/cities/{city_id}/public/summary")
async def public_city_summary(
    city_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiEnvelope[dict]:
    """Return current AQI, advisories, and pollutant snapshot — no auth needed."""

    # Verify city exists
    city_row = await db.execute(
        text("SELECT id, name, state FROM cities WHERE id = :id"),
        {"id": city_id},
    )
    city = city_row.fetchone()
    if not city:
        raise NotFoundError(f"City {city_id} not found")

    city_name = city[1]
    city_state = city[2]

    # Latest station readings (last 2 hrs)
    readings_row = await db.execute(
        text(
            """
            SELECT
                MAX(aqi)  AS avg_aqi,
                AVG(pm25) AS avg_pm25,
                AVG(pm10) AS avg_pm10,
                AVG(no2)  AS avg_no2,
                MAX(sr.ts) AS last_updated
            FROM station_readings sr
            JOIN stations s ON s.id = sr.station_id
            WHERE s.city_id = :city_id
              AND sr.aqi BETWEEN 0 AND 500
              AND (sr.pm25 IS NULL OR sr.pm25 <= 900)
              AND sr.ts >= NOW() - INTERVAL '24 hours'
            """
        ),
        {"city_id": city_id},
    )
    readings = readings_row.fetchone()

    avg_aqi = int(readings[0]) if readings and readings[0] else None
    avg_pm25 = round(float(readings[1]), 1) if readings and readings[1] else None
    avg_pm10 = round(float(readings[2]), 1) if readings and readings[2] else None
    avg_no2 = round(float(readings[3]), 1) if readings and readings[3] else None
    last_updated = readings[4].isoformat() if readings and readings[4] else None

    # AQI level label
    def _aqi_level(aqi: int | None) -> str:
        if aqi is None:
            return "Unknown"
        if aqi <= 50:
            return "Good"
        if aqi <= 100:
            return "Satisfactory"
        if aqi <= 200:
            return "Moderate"
        if aqi <= 300:
            return "Poor"
        if aqi <= 400:
            return "Very Poor"
        return "Severe"

    aqi_level = _aqi_level(avg_aqi)

    # Dominant source from latest attribution
    attr_row = await db.execute(
        text(
            """
            SELECT dominant_source
            FROM attributions
            WHERE city_id = :city_id
            ORDER BY computed_at DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    attr = attr_row.fetchone()
    dominant_source = attr[0] if attr else None

    # Latest advisories (EN + HI) — match current AQI level, fall back to most recent
    adv_row = await db.execute(
        text(
            """
            SELECT language, title, body
            FROM advisories
            WHERE city_id = :city_id
              AND language IN ('en', 'hi')
              AND aqi_level = :aqi_level
            ORDER BY created_at DESC
            LIMIT 10
            """
        ),
        {"city_id": city_id, "aqi_level": aqi_level},
    )
    adv_rows = adv_row.fetchall()

    advisories: dict[str, dict] = {}
    for row in adv_rows:
        lang = row[0]
        if lang not in advisories:
            advisories[lang] = {"title": row[1], "body": row[2]}

    # List all cities for the city selector
    cities_row = await db.execute(text("SELECT id, name, state FROM cities ORDER BY name"))
    all_cities = [{"id": r[0], "name": r[1], "state": r[2]} for r in cities_row.fetchall()]

    return ApiEnvelope(
        data={
            "city": {"id": city_id, "name": city_name, "state": city_state},
            "aqi": avg_aqi,
            "aqi_level": aqi_level,
            "dominant_source": dominant_source,
            "pollutants": {
                "pm25": avg_pm25,
                "pm10": avg_pm10,
                "no2": avg_no2,
            },
            "last_updated": last_updated,
            "advisories": advisories,
            "all_cities": all_cities,
        }
    )
