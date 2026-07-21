"""Reports — database queries."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_city_info(db: AsyncSession, city_id: str) -> dict | None:
    row = await db.execute(
        text("SELECT id, name, state, timezone FROM cities WHERE id = :id"),
        {"id": city_id},
    )
    r = row.fetchone()
    return dict(r._mapping) if r else None


async def get_aqi_stats(db: AsyncSession, city_id: str, days: int) -> dict:
    """Return current_avg_aqi, peak_aqi, and per-category hour counts."""
    result = await db.execute(
        text(
            """
            WITH city_stations AS (
                SELECT id FROM stations WHERE city_id = :city_id AND is_active = true
            ),
            readings AS (
                SELECT
                    sr.aqi,
                    DATE_TRUNC('hour', sr.ts) AS hour_bucket
                FROM station_readings sr
                WHERE sr.station_id IN (SELECT id FROM city_stations)
                  AND sr.ts >= NOW() - :days * INTERVAL '1 day'
                  AND sr.aqi IS NOT NULL
            ),
            current_readings AS (
                SELECT MAX(sr.aqi) AS current_avg
                FROM station_readings sr
                WHERE sr.station_id IN (SELECT id FROM city_stations)
                  AND sr.aqi BETWEEN 0 AND 500
                  AND (sr.pm25 IS NULL OR sr.pm25 <= 900)
                  AND sr.ts >= NOW() - INTERVAL '24 hours'
            ),
            hourly AS (
                SELECT hour_bucket, AVG(aqi) AS avg_aqi
                FROM readings
                GROUP BY hour_bucket
            )
            SELECT
                (SELECT current_avg FROM current_readings) AS current_avg_aqi,
                MAX(avg_aqi)                               AS peak_aqi,
                COUNT(*)                                   AS total_hours,
                SUM(CASE WHEN avg_aqi <= 50   THEN 1 ELSE 0 END) AS good_hours,
                SUM(CASE WHEN avg_aqi BETWEEN 51 AND 100  THEN 1 ELSE 0 END) AS satisfactory_hours,
                SUM(CASE WHEN avg_aqi BETWEEN 101 AND 200 THEN 1 ELSE 0 END) AS moderate_hours,
                SUM(CASE WHEN avg_aqi BETWEEN 201 AND 300 THEN 1 ELSE 0 END) AS poor_hours,
                SUM(CASE WHEN avg_aqi BETWEEN 301 AND 400 THEN 1 ELSE 0 END) AS very_poor_hours,
                SUM(CASE WHEN avg_aqi > 400  THEN 1 ELSE 0 END) AS severe_hours
            FROM hourly
            """
        ),
        {"city_id": city_id, "days": days},
    )
    row = result.fetchone()
    if not row:
        return {
            "current_avg_aqi": None,
            "peak_aqi_7d": None,
            "category_breakdown": {},
        }
    d = dict(row._mapping)
    total = d["total_hours"] or 1
    breakdown = {
        "Good": round(100 * (d["good_hours"] or 0) / total, 1),
        "Satisfactory": round(100 * (d["satisfactory_hours"] or 0) / total, 1),
        "Moderate": round(100 * (d["moderate_hours"] or 0) / total, 1),
        "Poor": round(100 * (d["poor_hours"] or 0) / total, 1),
        "Very Poor": round(100 * (d["very_poor_hours"] or 0) / total, 1),
        "Severe": round(100 * (d["severe_hours"] or 0) / total, 1),
    }
    return {
        "current_avg_aqi": float(d["current_avg_aqi"]) if d["current_avg_aqi"] else None,
        "peak_aqi_7d": float(d["peak_aqi"]) if d["peak_aqi"] else None,
        "category_breakdown": breakdown,
    }


async def get_top_enforcement_items(db: AsyncSession, city_id: str, limit: int = 3) -> list[dict]:
    rows = await db.execute(
        text(
            """
            SELECT
                eq.id, eq.priority_score, eq.status,
                es.name AS source_name, es.type AS source_type
            FROM enforcement_queue eq
            JOIN emission_sources es ON es.id = eq.emission_source_id
            WHERE eq.city_id = :city_id
            ORDER BY eq.priority_score DESC
            LIMIT :limit
            """
        ),
        {"city_id": city_id, "limit": limit},
    )
    return [dict(r._mapping) for r in rows.fetchall()]


async def get_advisory_count_by_language(db: AsyncSession, city_id: str) -> dict[str, int]:
    rows = await db.execute(
        text(
            """
            SELECT language, COUNT(*) AS cnt
            FROM advisories
            WHERE city_id = :city_id
            GROUP BY language
            ORDER BY language
            """
        ),
        {"city_id": city_id},
    )
    return {r.language: int(r.cnt) for r in rows.fetchall()}


async def get_forecast_summary(db: AsyncSession, city_id: str) -> dict:
    """Return next-24h peak AQI and the UTC hour at which it occurs."""
    rows = await db.execute(
        text(
            """
            SELECT predicted_aqi, EXTRACT(HOUR FROM forecast_for_ts) AS hour_of_day
            FROM forecasts
            WHERE city_id = :city_id
              AND is_stale = false
              AND forecast_for_ts BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
            ORDER BY predicted_aqi DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    row = rows.fetchone()
    if not row:
        return {"next_24h_peak_aqi": None, "dominant_hour": None}
    return {
        "next_24h_peak_aqi": float(row.predicted_aqi),
        "dominant_hour": int(row.hour_of_day),
    }


async def get_attribution_summary(db: AsyncSession, city_id: str) -> dict:
    row = await db.execute(
        text(
            """
            SELECT dominant_source, vehicular_pct, industrial_pct,
                   construction_pct, agricultural_pct, fire_pct, other_pct
            FROM attributions
            WHERE city_id = :city_id
            ORDER BY computed_at DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    )
    r = row.fetchone()
    if not r:
        return {"dominant_source": None, "breakdown": {}}
    d = dict(r._mapping)
    breakdown = {k.replace("_pct", ""): float(v or 0) for k, v in d.items() if k.endswith("_pct")}
    return {"dominant_source": d["dominant_source"], "breakdown": breakdown}


async def get_enforcement_stats(db: AsyncSession, city_id: str, days: int) -> dict:
    """Return enforcement action counts for the period and overall."""
    row = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'completed'
                    AND updated_at >= NOW() - :days * INTERVAL '1 day') AS completed_period,
                COUNT(*) FILTER (WHERE status = 'dispatched') AS dispatched_active,
                COUNT(*) FILTER (WHERE status = 'pending')    AS pending_count,
                COUNT(*) FILTER (WHERE status = 'completed')  AS completed_total
            FROM enforcement_queue
            WHERE city_id = :city_id
            """
        ),
        {"city_id": city_id, "days": days},
    )
    r = row.fetchone()
    if not r:
        return {
            "completed_period": 0,
            "dispatched_active": 0,
            "pending_count": 0,
            "completed_total": 0,
        }
    return {
        "completed_period": int(r.completed_period or 0),
        "dispatched_active": int(r.dispatched_active or 0),
        "pending_count": int(r.pending_count or 0),
        "completed_total": int(r.completed_total or 0),
    }


async def get_ward_aqi_table(db: AsyncSession, city_id: str, days: int) -> list[dict]:
    rows = await db.execute(
        text(
            """
            SELECT
                w.id AS ward_id,
                w.name AS ward_name,
                AVG(sr.aqi) AS avg_aqi,
                COUNT(sr.aqi) AS reading_count
            FROM wards w
            LEFT JOIN stations s ON s.ward_id = w.id AND s.city_id = :city_id AND s.is_active = true
            LEFT JOIN station_readings sr
                ON sr.station_id = s.id
                AND sr.ts >= NOW() - :days * INTERVAL '1 day'
                AND sr.aqi IS NOT NULL
            WHERE w.city_id = :city_id
            GROUP BY w.id, w.name
            ORDER BY avg_aqi DESC NULLS LAST
            """
        ),
        {"city_id": city_id, "days": days},
    )
    return [
        {
            "ward_id": str(r.ward_id),
            "ward_name": r.ward_name,
            "avg_aqi": float(r.avg_aqi) if r.avg_aqi is not None else None,
            "reading_count": int(r.reading_count),
        }
        for r in rows.fetchall()
    ]
