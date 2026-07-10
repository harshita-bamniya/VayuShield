"""CAAQMS / CPCB connector.

Two data paths:
  1. Real — data.gov.in CPCB API (requires CPCB_API_KEY in .env).
     Fetches all stations for a city in one call; returns grouped readings.
  2. Mock fallback — statistically realistic Delhi AQI values when no key
     is set or the API is unavailable.

API: https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69
Returns one row per pollutant per station; we group by station name.
"""

import math
import random
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.modules.ingestion.schemas import StationReadingIn

CPCB_API_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"

# Pollutant field names as returned by data.gov.in
_POLLUTANT_MAP = {
    "PM2.5": "pm25",
    "PM10": "pm10",
    "NO2": "no2",
    "SO2": "so2",
    "CO": "co",
    "OZONE": "o3",
    "O3": "o3",
    "NH3": None,  # not stored in our schema
}


# ── Public API used by service.py ─────────────────────────────────────────────


async def fetch_city_readings_cpcb(city_name: str) -> dict[str, dict]:
    """Fetch all station readings for a city from data.gov.in CPCB API.

    Returns a dict keyed by lowercase station name fragment →
      {"pm25": float|None, "pm10": ..., "no2": ..., "so2": ..., "co": ..., "o3": ...}

    Returns {} if CPCB_API_KEY is not set or the call fails.
    """
    api_key = settings.CPCB_API_KEY
    if not api_key:
        return {}

    # data.gov.in uses state name "Delhi" for the UT; normalise common names
    state_param = _city_to_state(city_name)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                CPCB_API_URL,
                params={
                    "api-key": api_key,
                    "format": "json",
                    "limit": 500,
                    "filters[state]": state_param,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("CPCB API fetch failed", city=city_name, error=str(exc))
        return {}

    records = data.get("records", [])
    grouped: dict[str, dict] = {}

    for row in records:
        station_raw: str = row.get("station", "")
        pollutant: str = row.get("pollutant_id", "")
        avg_raw: str = row.get("avg_value", "NA")

        field = _POLLUTANT_MAP.get(pollutant)
        if field is None:
            continue

        key = station_raw.lower()
        if key not in grouped:
            grouped[key] = {
                "_station_raw": station_raw,
                "pm25": None,
                "pm10": None,
                "no2": None,
                "so2": None,
                "co": None,
                "o3": None,
            }

        if avg_raw and avg_raw.upper() != "NA":
            try:
                grouped[key][field] = float(avg_raw)
            except ValueError:
                pass

    logger.info("CPCB API returned stations", city=city_name, count=len(grouped))
    return grouped


def match_station_reading(
    cpcb_data: dict[str, dict],
    station_code: str,
    station_id: str,
    ts: datetime,
) -> StationReadingIn | None:
    """Match a DB station to CPCB data by fuzzy name lookup on station_code keywords.

    station_code examples: "DPCC_ANAND_VIHAR", "DPCC_ITO", "IITM_PUSA"
    CPCB station names:    "Anand Vihar, Delhi - DPCC", "ITO, Delhi - DPCC"
    """
    if not cpcb_data:
        return None

    # Extract meaningful keywords from the station code (drop agency prefix)
    parts = station_code.lower().split("_")
    # Remove common agency prefixes
    agencies = {"dpcc", "iitm", "cpcb", "mpcb", "bspcb", "kspcb"}
    keywords = [p for p in parts if p not in agencies and len(p) > 1]

    best_key = None
    best_score = 0
    for key in cpcb_data:
        score = sum(1 for kw in keywords if kw in key)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key is None or best_score == 0:
        return None

    row = cpcb_data[best_key]
    # Need at least PM2.5 or PM10 to be useful
    if row.get("pm25") is None and row.get("pm10") is None:
        return None

    logger.info(
        "Matched CPCB station",
        code=station_code,
        cpcb_station=row["_station_raw"],
        score=best_score,
    )
    return StationReadingIn(
        station_id=station_id,
        ts=ts,
        pm25=row.get("pm25"),
        pm10=row.get("pm10"),
        no2=row.get("no2"),
        so2=row.get("so2"),
        co=row.get("co"),
        o3=row.get("o3"),
    )


async def fetch_station_readings(
    station_code: str,
    station_id: str,
    ts: datetime,
) -> StationReadingIn:
    """Per-station fallback: always returns a mock reading (used when CPCB bulk fails)."""
    return _mock_reading(station_id, ts)


# ── City → state name mapping for data.gov.in filter ─────────────────────────


def _city_to_state(city_name: str) -> str:
    _MAP = {
        # Delhi / NCR
        "new delhi": "Delhi",
        "delhi": "Delhi",
        "gurugram": "Haryana",
        "gurgaon": "Haryana",
        "faridabad": "Haryana",
        "noida": "Uttar Pradesh",
        "ghaziabad": "Uttar Pradesh",
        # Maharashtra
        "mumbai": "Maharashtra",
        "pune": "Maharashtra",
        "nagpur": "Maharashtra",
        "nashik": "Maharashtra",
        "aurangabad": "Maharashtra",
        "solapur": "Maharashtra",
        "kolhapur": "Maharashtra",
        "amravati": "Maharashtra",
        # Karnataka
        "bengaluru": "Karnataka",
        "bangalore": "Karnataka",
        "mysuru": "Karnataka",
        "mysore": "Karnataka",
        "hubli": "Karnataka",
        "mangaluru": "Karnataka",
        # Telangana & Andhra Pradesh
        "hyderabad": "Telangana",
        "warangal": "Telangana",
        "visakhapatnam": "Andhra Pradesh",
        "vijayawada": "Andhra Pradesh",
        "guntur": "Andhra Pradesh",
        "tirupati": "Andhra Pradesh",
        # Tamil Nadu
        "chennai": "Tamil Nadu",
        "coimbatore": "Tamil Nadu",
        "madurai": "Tamil Nadu",
        "tiruchirappalli": "Tamil Nadu",
        "trichy": "Tamil Nadu",
        "salem": "Tamil Nadu",
        "tirunelveli": "Tamil Nadu",
        # West Bengal
        "kolkata": "West Bengal",
        "howrah": "West Bengal",
        "durgapur": "West Bengal",
        "asansol": "West Bengal",
        # Gujarat
        "ahmedabad": "Gujarat",
        "surat": "Gujarat",
        "vadodara": "Gujarat",
        "rajkot": "Gujarat",
        "bhavnagar": "Gujarat",
        "jamnagar": "Gujarat",
        # Rajasthan
        "jaipur": "Rajasthan",
        "jodhpur": "Rajasthan",
        "udaipur": "Rajasthan",
        "kota": "Rajasthan",
        "ajmer": "Rajasthan",
        "bikaner": "Rajasthan",
        # Uttar Pradesh
        "lucknow": "Uttar Pradesh",
        "kanpur": "Uttar Pradesh",
        "agra": "Uttar Pradesh",
        "varanasi": "Uttar Pradesh",
        "allahabad": "Uttar Pradesh",
        "prayagraj": "Uttar Pradesh",
        "meerut": "Uttar Pradesh",
        "bareilly": "Uttar Pradesh",
        "moradabad": "Uttar Pradesh",
        "aligarh": "Uttar Pradesh",
        # Bihar
        "patna": "Bihar",
        "gaya": "Bihar",
        "muzaffarpur": "Bihar",
        # Madhya Pradesh
        "bhopal": "Madhya Pradesh",
        "indore": "Madhya Pradesh",
        "jabalpur": "Madhya Pradesh",
        "gwalior": "Madhya Pradesh",
        "ujjain": "Madhya Pradesh",
        # Punjab & Haryana
        "chandigarh": "Chandigarh",
        "ludhiana": "Punjab",
        "amritsar": "Punjab",
        "jalandhar": "Punjab",
        "patiala": "Punjab",
        "ambala": "Haryana",
        "hisar": "Haryana",
        "rohtak": "Haryana",
        "panipat": "Haryana",
        # Other states
        "bhubaneswar": "Odisha",
        "cuttack": "Odisha",
        "rourkela": "Odisha",
        "ranchi": "Jharkhand",
        "jamshedpur": "Jharkhand",
        "dhanbad": "Jharkhand",
        "raipur": "Chhattisgarh",
        "bhilai": "Chhattisgarh",
        "dehradun": "Uttarakhand",
        "haridwar": "Uttarakhand",
        "shimla": "Himachal Pradesh",
        "srinagar": "Jammu & Kashmir",
        "jammu": "Jammu & Kashmir",
        "guwahati": "Assam",
        "dibrugarh": "Assam",
        "thiruvananthapuram": "Kerala",
        "trivandrum": "Kerala",
        "kochi": "Kerala",
        "kozhikode": "Kerala",
        "thrissur": "Kerala",
        "puducherry": "Puducherry",
        "pondicherry": "Puducherry",
        "port blair": "Andaman and Nicobar Islands",
        "panaji": "Goa",
        "margao": "Goa",
        "aizawl": "Mizoram",
        "imphal": "Manipur",
        "kohima": "Nagaland",
        "agartala": "Tripura",
        "shillong": "Meghalaya",
        "gangtok": "Sikkim",
        "itanagar": "Arunachal Pradesh",
    }
    return _MAP.get(city_name.lower(), city_name)


# ── Mock fallback ─────────────────────────────────────────────────────────────


def _mock_reading(station_id: str, ts: datetime) -> StationReadingIn:
    """Generate a realistic PM2.5/PM10/AQI value for a Delhi station."""
    hour = ts.hour

    diurnal = 1.0 + 0.4 * (
        math.exp(-0.5 * ((hour - 8) / 2) ** 2) + math.exp(-0.5 * ((hour - 20) / 2) ** 2)
    )

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
    """Generate mock readings between start and end — used by seed script."""
    from datetime import timedelta

    readings = []
    current = start
    while current <= end:
        readings.append(_mock_reading(station_id, current))
        current = start + timedelta(hours=interval_hours * (len(readings)))
        if current > end:
            break
    return readings
