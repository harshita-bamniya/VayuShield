"""NASA FIRMS fire hotspot connector.

Fetches active fire detections from NASA FIRMS (Fire Information for Resource
Management System) within a bounding box around the city.

API: https://firms.modaps.eosdis.nasa.gov/api/
Free MAP_KEY available at: https://firms.modaps.eosdis.nasa.gov/api/area/

Set FIRMS_MAP_KEY in .env to activate real data fetching.
Falls back to an empty list (no fire data) if key is not configured.
"""

import csv
import io
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import logger

FIRMS_API_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Delhi bounding box (lat_min, lat_max, lon_min, lon_max)
DELHI_BBOX = (28.4, 28.9, 76.8, 77.4)


async def fetch_fire_hotspots(
    city_id: str,
    bbox: tuple[float, float, float, float] = DELHI_BBOX,
    days_back: int = 1,
) -> list[dict]:
    """Fetch fire hotspots from NASA FIRMS for the given bounding box.

    Returns list of dicts for insert_fire_hotspot().
    Falls back to empty list if MAP_KEY not configured.
    """
    map_key = getattr(settings, "FIRMS_MAP_KEY", "")
    if not map_key:
        logger.info("FIRMS_MAP_KEY not set — skipping fire hotspot fetch")
        return []

    lat_min, lat_max, lon_min, lon_max = bbox
    area = f"{lon_min},{lat_min},{lon_max},{lat_max}"

    url = f"{FIRMS_API_URL}/{map_key}/VIIRS_SNPP_NRT/{area}/{days_back}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return _parse_firms_csv(resp.text, city_id)
    except Exception as exc:
        logger.warning("FIRMS fetch failed", error=str(exc))
        return []


def _parse_firms_csv(csv_text: str, city_id: str) -> list[dict]:
    hotspots = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            acq_date = row["acq_date"]  # YYYY-MM-DD
            acq_time = row["acq_time"]  # HHMM
            hour = int(acq_time[:2]) if len(acq_time) >= 2 else 0
            minute = int(acq_time[2:4]) if len(acq_time) >= 4 else 0
            dt_str = f"{acq_date} {hour:02d}:{minute:02d}:00"
            detected_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            confidence_raw = row.get("confidence", "50")
            # VIIRS confidence: 'l', 'n', 'h' → map to 33, 66, 90
            conf_map = {"l": 33.0, "n": 66.0, "h": 90.0}
            confidence = conf_map.get(
                confidence_raw, float(confidence_raw) if confidence_raw.isdigit() else 50.0
            )
            frp = float(row["frp"]) if row.get("frp") else None
            hotspots.append(
                {
                    "city_id": city_id,
                    "detected_at": detected_at,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "confidence": confidence,
                    "source": "NASA_FIRMS",
                    "frp": frp,
                }
            )
        except (KeyError, ValueError):
            continue
    return hotspots
