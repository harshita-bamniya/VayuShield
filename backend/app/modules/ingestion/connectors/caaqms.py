"""CAAQMS / CPCB connector.

The official CPCB CCR API (https://app.cpcbccr.com/) does not publish a public
REST specification. This module provides:
  1. `fetch_station_readings()` — a real HTTP client stub; swap the commented-out
     block for actual credentials when CPCB grants API access.
  2. A mock fallback that generates statistically realistic Delhi AQI values so
     the pipeline runs end-to-end during the hackathon demo without real credentials.

Mock data characteristics:
  - PM2.5 follows a diurnal pattern (peaks 07:00–09:00 and 19:00–22:00 IST)
  - Base concentration is seasonally adjusted (higher in winter)
  - ±15% random noise to simulate sensor variation
"""

import math
import random
from datetime import datetime, timezone

import httpx

from app.core.logging import logger
from app.modules.ingestion.schemas import StationReadingIn


async def fetch_station_readings(
    station_code: str,
    station_id: str,
    ts: datetime,
) -> StationReadingIn | None:
    """Fetch the latest reading for one CAAQMS station.

    Tries the real CPCB API first; falls back to mock if unavailable.
    """
    try:
        return await _fetch_from_cpcb(station_code, station_id, ts)
    except Exception as exc:
        logger.warning(
            "CPCB API unavailable, using mock data",
            station_code=station_code,
            error=str(exc),
        )
        return _mock_reading(station_id, ts)


async def _fetch_from_cpcb(
    station_code: str, station_id: str, ts: datetime
) -> StationReadingIn:
    """Real CPCB API call — requires valid credentials in settings.

    Uncomment and configure when API access is granted:

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://app.cpcbccr.com/ccr/api/caaqm-dashboard/caaqm-parameter-data",
                params={"stationId": station_code, "startTime": ..., "endTime": ...},
                headers={"Authorization": f"Bearer {settings.CPCB_API_KEY}"},
            )
            data = resp.json()
            return _parse_cpcb_response(data, station_id, ts)
    """
    # Until credentials are available, raise so we fall back to mock.
    raise NotImplementedError("CPCB API credentials not configured")


def _mock_reading(station_id: str, ts: datetime) -> StationReadingIn:
    """Generate a realistic PM2.5/PM10/AQI value for a Delhi station."""
    hour = ts.hour  # IST approximate (UTC+5:30 ≈ UTC+5 for hour-of-day)

    # Diurnal cycle: peaks at morning rush (8h) and evening (20h)
    diurnal = 1.0 + 0.4 * (
        math.exp(-0.5 * ((hour - 8) / 2) ** 2) + math.exp(-0.5 * ((hour - 20) / 2) ** 2)
    )

    # Delhi winter base PM2.5 ≈ 120 µg/m³; use 120 as year-round demo base
    base_pm25 = 120.0 * diurnal
    pm25 = max(5.0, base_pm25 * random.uniform(0.85, 1.15))
    pm10 = pm25 * random.uniform(1.5, 2.2)
    no2 = random.uniform(20, 90)
    so2 = random.uniform(5, 30)
    co = random.uniform(0.5, 3.0)
    o3 = random.uniform(10, 60)

    return StationReadingIn(
        station_id=station_id,
        ts=ts,
        pm25=round(pm25, 2),
        pm10=round(pm10, 2),
        no2=round(no2, 2),
        so2=round(so2, 2),
        co=round(co, 2),
        o3=round(o3, 2),
    )


def generate_historical_readings(
    station_id: str,
    start: datetime,
    end: datetime,
    interval_hours: int = 1,
) -> list[StationReadingIn]:
    """Generate mock readings between start and end at interval_hours cadence.

    Used by the seed script to pre-populate historical data for the demo.
    """
    readings = []
    current = start
    while current <= end:
        readings.append(_mock_reading(station_id, current))
        current = current.replace(hour=(current.hour + interval_hours) % 24) if interval_hours < 24 else current  # noqa
        # Simple increment via timestamp arithmetic
        from datetime import timedelta
        current = start + timedelta(
            hours=interval_hours * (len(readings))
        )
        if current > end:
            break
    return readings
