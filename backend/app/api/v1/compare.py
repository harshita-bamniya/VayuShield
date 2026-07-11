"""Multi-city comparison API — sysadmin only."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["compare"])


class CitySnapshot(BaseModel):
    city_id: str
    city_name: str
    current_aqi: int | None
    aqi_category: str | None
    trend_delta: int | None  # current avg minus 6h-ago avg (negative = improving)
    peak_forecast_aqi: int | None  # next 72h peak
    dominant_source: str | None
    attribution_confidence: float | None
    pending_enforcement: int
    dispatched_enforcement: int
    completed_enforcement: int
    intervention_effectiveness: float | None  # completed / (completed + pending) [0–1]
    aqi_history_24h: list[dict]  # [{hour, aqi}] for trend sparkline


class CompareOut(BaseModel):
    generated_at: datetime
    cities: list[CitySnapshot]


@router.get("/cities/compare", response_model=ApiEnvelope[CompareOut])
async def compare_cities(
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_role("sysadmin")),
):
    """Return a side-by-side snapshot of all cities for the comparison dashboard."""
    now = datetime.now(UTC)

    # All cities
    city_rows = await db.execute(text("SELECT id, name FROM cities ORDER BY name"))
    cities = [{"id": r[0], "name": r[1]} for r in city_rows.fetchall()]

    snapshots: list[CitySnapshot] = []

    for city in cities:
        cid = city["id"]

        # Current AQI (avg of last 30 min)
        aqi_now_row = await db.execute(
            text("""
                SELECT ROUND(AVG(sr.aqi))::int
                FROM station_readings sr
                JOIN stations s ON s.id = sr.station_id
                WHERE s.city_id = :cid AND sr.aqi IS NOT NULL
                  AND sr.ts >= NOW() - INTERVAL '30 minutes'
            """),
            {"cid": cid},
        )
        current_aqi: int | None = aqi_now_row.scalar_one_or_none()

        # AQI 6h ago (avg over 30-min window centred at -6h)
        aqi_6h_row = await db.execute(
            text("""
                SELECT ROUND(AVG(sr.aqi))::int
                FROM station_readings sr
                JOIN stations s ON s.id = sr.station_id
                WHERE s.city_id = :cid AND sr.aqi IS NOT NULL
                  AND sr.ts BETWEEN NOW() - INTERVAL '6.5 hours' AND NOW() - INTERVAL '5.5 hours'
            """),
            {"cid": cid},
        )
        aqi_6h_ago: int | None = aqi_6h_row.scalar_one_or_none()
        trend_delta: int | None = None
        if current_aqi is not None and aqi_6h_ago is not None:
            trend_delta = current_aqi - aqi_6h_ago

        # AQI category
        def _category(aqi: int | None) -> str | None:
            if aqi is None:
                return None
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

        # Peak forecast next 72h
        peak_row = await db.execute(
            text("""
                SELECT MAX(predicted_aqi) FROM forecasts
                WHERE city_id = :cid AND ward_id IS NULL AND NOT is_stale
                  AND forecast_for_ts >= NOW()
            """),
            {"cid": cid},
        )
        peak_forecast: int | None = peak_row.scalar_one_or_none()

        # Dominant source + confidence from latest attribution
        attr_row = await db.execute(
            text("""
                SELECT dominant_source, notes
                FROM attributions WHERE city_id = :cid ORDER BY computed_at DESC LIMIT 1
            """),
            {"cid": cid},
        )
        attr = attr_row.fetchone()
        dominant_source: str | None = None
        confidence: float | None = None
        if attr:
            dominant_source = attr[0]
            if attr[1]:
                try:
                    parts = dict(p.split("=") for p in attr[1].split(" | ") if "=" in p)
                    confidence = float(parts["confidence"]) if "confidence" in parts else None
                except Exception:
                    pass

        # Enforcement counts
        eq_row = await db.execute(
            text("""
                SELECT
                  COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                  COUNT(*) FILTER (WHERE status = 'dispatched') AS dispatched,
                  COUNT(*) FILTER (WHERE status = 'completed') AS completed
                FROM enforcement_queue WHERE city_id = :cid
            """),
            {"cid": cid},
        )
        eq = eq_row.fetchone()
        pending_cnt = int(eq[0] or 0)
        dispatched_cnt = int(eq[1] or 0)
        completed_cnt = int(eq[2] or 0)
        total_actionable = completed_cnt + pending_cnt + dispatched_cnt
        effectiveness: float | None = (
            round(completed_cnt / total_actionable, 2) if total_actionable > 0 else None
        )

        # 24h AQI history for sparkline (hourly buckets)
        hist_rows = await db.execute(
            text("""
                SELECT DATE_TRUNC('hour', sr.ts) AS hour_bucket,
                       ROUND(AVG(sr.aqi))::int AS avg_aqi
                FROM station_readings sr
                JOIN stations s ON s.id = sr.station_id
                WHERE s.city_id = :cid AND sr.aqi IS NOT NULL
                  AND sr.ts >= NOW() - INTERVAL '24 hours'
                GROUP BY hour_bucket ORDER BY hour_bucket
            """),
            {"cid": cid},
        )
        aqi_history = [{"hour": row[0].isoformat(), "aqi": row[1]} for row in hist_rows.fetchall()]

        snapshots.append(
            CitySnapshot(
                city_id=cid,
                city_name=city["name"],
                current_aqi=current_aqi,
                aqi_category=_category(current_aqi),
                trend_delta=trend_delta,
                peak_forecast_aqi=peak_forecast,
                dominant_source=dominant_source,
                attribution_confidence=confidence,
                pending_enforcement=pending_cnt,
                dispatched_enforcement=dispatched_cnt,
                completed_enforcement=completed_cnt,
                intervention_effectiveness=effectiveness,
                aqi_history_24h=aqi_history,
            )
        )

    return ApiEnvelope(data=CompareOut(generated_at=now, cities=snapshots))
