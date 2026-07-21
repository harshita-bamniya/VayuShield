"""TomTom Traffic Flow connector.

Fetches real-time congestion ratio (current speed / free-flow speed) for
key road segments around each city.

API: TomTom Traffic Flow — https://developer.tomtom.com/traffic-api/
Free tier: 2,500 requests/day — no credit card required.
Key: https://developer.tomtom.com/ → register → My Apps → create key.

Set TOMTOM_API_KEY in .env to activate real fetching.
Falls back to realistic mock data (deterministic per city+hour) otherwise.

Congestion ratio interpretation:
  < 1.0   Faster than free-flow (road is clear)
  1.0–1.5 Normal urban traffic
  1.5–2.5 Moderate congestion
  > 2.5   Heavy congestion — significant vehicular emission boost
"""

import hashlib
import uuid
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import logger

TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

# Representative road segments per city: (segment_id, name, lat, lon)
CITY_SEGMENTS: dict[str, list[tuple[str, str, float, float]]] = {
    "Delhi": [
        ("DEL-NH48", "NH48 — Gurgaon Expressway", 28.5022, 77.0890),
        ("DEL-RING", "Ring Road — ITO", 28.6290, 77.2415),
        ("DEL-OUTER", "Outer Ring Road — Rohini", 28.7200, 77.1100),
        ("DEL-GTK", "GT Karnal Road — Mukarba", 28.7260, 77.1700),
        ("DEL-MB", "MB Road — Badarpur", 28.5100, 77.2940),
    ],
    "Mumbai": [
        ("MUM-WEH", "Western Express Hwy — Andheri", 19.1197, 72.8468),
        ("MUM-EEH", "Eastern Express Hwy — Kurla", 19.0680, 72.8956),
        ("MUM-SION", "Sion-Panvel Hwy", 19.0430, 72.9250),
        ("MUM-LBS", "LBS Marg — Ghatkopar", 19.0900, 72.9080),
        ("MUM-WC", "Worli — Coastal Road", 18.9950, 72.8139),
    ],
    "Bengaluru": [
        ("BLR-ORR", "Outer Ring Road — Marathahalli", 12.9588, 77.6975),
        ("BLR-NICE", "NICE Road — Hosur", 12.8721, 77.6010),
        ("BLR-MG", "MG Road — Central", 12.9747, 77.6174),
        ("BLR-BEL", "Bellary Road — Hebbal", 13.0354, 77.5970),
        ("BLR-ECO", "Ecospace — Sarjapur", 12.9099, 77.6849),
    ],
    "_default": [
        ("SEG-1", "Main Arterial Road", 0.0, 0.0),
        ("SEG-2", "Ring Road", 0.01, 0.01),
        ("SEG-3", "National Highway", 0.02, -0.01),
        ("SEG-4", "Urban Connector", -0.01, 0.02),
        ("SEG-5", "Industrial Corridor", -0.02, -0.02),
    ],
}

# Typical peak-hour congestion by city (ratio scale)
_CITY_CONGESTION_BASE: dict[str, float] = {
    "Delhi": 2.1,
    "Mumbai": 2.4,
    "Bengaluru": 2.6,
    "Chennai": 1.9,
    "Kolkata": 1.8,
    "Hyderabad": 1.7,
    "Pune": 1.6,
}
_DEFAULT_CONGESTION = 1.5


def _mock_congestion(city_name: str, segment_id: str, ts: datetime) -> float:
    """Deterministic mock congestion ratio — varies by city, segment, and hour."""
    base = _CITY_CONGESTION_BASE.get(city_name, _DEFAULT_CONGESTION)
    hour = ts.hour
    # Morning/evening peak factors
    if 8 <= hour <= 10 or 17 <= hour <= 20:
        peak_factor = 1.3
    elif 11 <= hour <= 16:
        peak_factor = 0.9
    else:
        peak_factor = 0.6  # night / early morning
    seed = int(hashlib.md5(f"{segment_id}{ts.date()}".encode()).hexdigest(), 16)
    variance = ((seed % 1000) / 1000 - 0.5) * 0.4
    ratio = base * peak_factor * (1 + variance * 0.2)
    return round(max(0.5, min(4.0, ratio)), 2)


async def fetch_traffic_segments(
    city_id: str,
    city_name: str,
    city_lat: float,
    city_lon: float,
) -> list[dict]:
    """Fetch congestion ratio for each road segment in the city.

    Returns list of dicts ready for DB insert.
    Falls back to mock data if TOMTOM_API_KEY is not set.
    """
    api_key = getattr(settings, "TOMTOM_API_KEY", "")
    segments = CITY_SEGMENTS.get(city_name, CITY_SEGMENTS["_default"])
    if segments[0][2] == 0.0:  # default segments — offset around city centre
        segments = [(s[0], s[1], city_lat + s[2], city_lon + s[3]) for s in segments]

    ts = datetime.now(UTC)

    if not api_key:
        logger.info("TOMTOM_API_KEY not set — using mock traffic data", city_name=city_name)
        return [_build_mock_snapshot(city_id, city_name, seg, ts) for seg in segments]

    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        for seg_id, seg_name, lat, lon in segments:
            try:
                resp = await client.get(
                    TOMTOM_FLOW_URL,
                    params={"key": api_key, "point": f"{lat},{lon}", "unit": "KMPH"},
                )
                resp.raise_for_status()
                data = resp.json().get("flowSegmentData", {})
                current_speed = float(data.get("currentSpeed", 0) or 0)
                free_flow = float(data.get("freeFlowSpeed", 1) or 1)
                congestion = round(free_flow / max(current_speed, 1), 2)
                results.append(
                    {
                        "id": str(uuid.uuid4()),
                        "city_id": city_id,
                        "ts": ts,
                        "segment_id": seg_id,
                        "segment_name": seg_name,
                        "congestion_ratio": congestion,
                        "current_speed": current_speed,
                        "free_flow_speed": free_flow,
                        "lat": lat,
                        "lon": lon,
                        "is_mock": False,
                    }
                )
            except Exception as exc:
                logger.warning("TomTom fetch failed for segment", segment=seg_id, error=str(exc))
                results.append(
                    _build_mock_snapshot(city_id, city_name, (seg_id, seg_name, lat, lon), ts)
                )
    return results


def _build_mock_snapshot(
    city_id: str,
    city_name: str,
    seg: tuple[str, str, float, float],
    ts: datetime,
) -> dict:
    seg_id, seg_name, lat, lon = seg
    ratio = _mock_congestion(city_name, seg_id, ts)
    free_flow = 60.0
    current = round(free_flow / ratio, 1)
    return {
        "id": str(uuid.uuid4()),
        "city_id": city_id,
        "ts": ts,
        "segment_id": seg_id,
        "segment_name": seg_name,
        "congestion_ratio": ratio,
        "current_speed": current,
        "free_flow_speed": free_flow,
        "lat": lat,
        "lon": lon,
        "is_mock": True,
    }


def congestion_label(ratio: float) -> str:
    if ratio < 1.0:
        return "Clear"
    if ratio < 1.5:
        return "Normal"
    if ratio < 2.5:
        return "Moderate"
    return "Heavy"
