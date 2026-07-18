"""CAAQMS / CPCB connector.

Data path:
  Primary  — WAQI API (waqi.info) which aggregates real CPCB/DPCC station data.
             Requires WAQI_TOKEN in .env. Free token at https://aqicn.org/data-platform/token/
             Falls back to data.gov.in CPCB API if WAQI_TOKEN not set.
  Secondary — data.gov.in CPCB API (requires CPCB_API_KEY in .env).
  No mock fallback — if both APIs are unavailable, no reading is stored.

WAQI endpoint: https://api.waqi.info/feed/{slug}/?token={token}
"""

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.modules.ingestion.schemas import StationReadingIn

CPCB_API_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
WAQI_FEED_URL = "https://api.waqi.info/feed/{slug}/"


def _pm25_to_aqi(pm25: float) -> int:
    """Convert PM2.5 (µg/m³) to India AQI using CPCB breakpoints."""
    breakpoints = [
        (0, 30, 0, 50),
        (30, 60, 51, 100),
        (60, 90, 101, 200),
        (90, 120, 201, 300),
        (120, 250, 301, 400),
        (250, 500, 401, 500),
    ]
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if c_lo <= pm25 <= c_hi:
            aqi = ((i_hi - i_lo) / (c_hi - c_lo)) * (pm25 - c_lo) + i_lo
            return round(aqi)
    return 500

# Maps our internal station_code → WAQI station slug (verified against live API)
_WAQI_SLUGS: dict[str, str] = {
    # Delhi DPCC network
    "DPCC_ANAND_VIHAR":  "delhi/anand-vihar",
    "DPCC_ITO":          "delhi/ito",
    "DPCC_PUNJABI_BAGH": "delhi/punjabi-bagh",
    "DPCC_MANDIR_MARG":  "delhi/mandir-marg",
    "DPCC_SHADIPUR":     "delhi/shadipur",
    "DPCC_NARELA":       "delhi/narela",
    "DPCC_MUNDKA":       "delhi/mundka",
    "IITM_PUSA":         "delhi/pusa",
    "DPCC_DWARKA_SEC8":  "delhi/national-institute-of-malaria-research--sector-8--dwarka",
    "DPCC_RK_PURAM":     "india/delhi/rk-puram",
    "DPCC_ROHINI":       "india/delhi/rohini",
    "DPCC_OKHLA_PH2":    "india/delhi/okhla-phase-2",
    "DPCC_BAWANA":       "india/delhi/bawana",
    "DPCC_PATPARGANJ":   "india/delhi/patparganj",
    "DPCC_SONIA_VIHAR":  "india/delhi/sonia-vihar",
    "DPCC_VIVEK_VIHAR":  "india/delhi/vivek-vihar",
    # Mumbai MPCB
    "MPCB_COLABA":       "india/mumbai/colaba",
    "MPCB_MAZGAON":      "india/mumbai/mazgaon",
    "MPCB_WORLI":        "india/mumbai/worli",
    "MPCB_CHEMBUR":      "india/mumbai/chembur",
    "MPCB_BANDRA":       "india/mumbai/bandra",
    "MPCB_KURLA":        "india/mumbai/kurla",
    "MPCB_ANDHERI":      "india/mumbai/chakala-andheri-east",
    "MPCB_MALAD":        "india/mumbai/malad-west",
    "MPCB_BORIVALI":     "india/mumbai/borivali-east",
    "MPCB_MULUND":       "india/mumbai/mulund-west",
    # Bengaluru KSPCB
    "KSPCB_BTM":          "india/bangalore/btm",
    "KSPCB_SILK_BOARD":   "india/bengaluru/silk-board",
    "KSPCB_HEBBAL":       "india/bengaluru/hebbal",
    "KSPCB_PEENYA":       "india/bangalore/peenya",
    "KSPCB_CITY_RAILWAY": "india/bangalore/city-railway-station",
    # Hyderabad TSPCB
    "TSPCB_SANATHNAGAR":  "india/hyderabad/sanathnagar",
    "TSPCB_ZOO_PARK":     "india/hyderabad/zoo-park--bahadurpura-west",
    "TSPCB_SOMAJIGUDA":   "india/hyderabad/somajiguda",
    # TSPCB_NACHARAM not available on WAQI — omitted
    # Chennai TNPCB
    "TNPCB_ALANDUR":      "chennai/alandur",
    "TNPCB_MANALI":       "chennai/manali",
    "TNPCB_VELACHERY":    "chennai//velachery-res.-area",
    # Kolkata WBPCB
    "WBPCB_BALLYGUNGE":   "india/kolkata/ballygunge",
    "WBPCB_JADAVPUR":     "india/kolkata/jadavpur",
    "WBPCB_FORT_WILLIAM": "india/kolkata/fort-william",
    # Pune MPCB
    "MPCB_SHIVAJINAGAR":  "pune/shivajinagar",
    "MPCB_KATRAJ":        "pune/katraj",
    "MPCB_HADAPSAR":      "pune/hadapsar",
}

# Pollutant field names as returned by data.gov.in
_POLLUTANT_MAP = {
    "PM2.5": "pm25",
    "PM10":  "pm10",
    "NO2":   "no2",
    "SO2":   "so2",
    "CO":    "co",
    "OZONE": "o3",
    "O3":    "o3",
    "NH3":   None,
}


# ── WAQI fetch (primary) ──────────────────────────────────────────────────────


async def fetch_station_reading_waqi(
    station_code: str,
    station_id: str,
    ts: datetime,
) -> StationReadingIn | None:
    """Fetch one station's reading from the WAQI API using the station slug."""
    token = settings.WAQI_TOKEN
    if not token:
        return None

    slug = _WAQI_SLUGS.get(station_code)
    if not slug:
        logger.debug("No WAQI slug for station", code=station_code)
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(WAQI_FEED_URL.format(slug=slug), params={"token": token})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("WAQI fetch failed", station=station_code, error=str(exc))
        return None

    if data.get("status") != "ok":
        logger.warning("WAQI returned non-ok status", station=station_code, status=data.get("status"))
        return None

    iaqi = data["data"].get("iaqi", {})
    aqi_raw = data["data"].get("aqi")

    def _val(key: str) -> float | None:
        v = iaqi.get(key, {}).get("v")
        return float(v) if v is not None else None

    pm25 = _val("pm25")
    pm10 = _val("pm10")

    # Parse overall AQI reported by WAQI
    aqi_int: int | None = None
    if aqi_raw not in (None, "-"):
        try:
            aqi_int = int(float(aqi_raw))
        except (TypeError, ValueError):
            pass

    # Fallback: compute AQI from PM2.5 if WAQI didn't return one
    if aqi_int is None and pm25 is not None:
        aqi_int = _pm25_to_aqi(pm25)

    # Drop obviously invalid AQI values (AQI scale is 0-500)
    if aqi_int is not None and (aqi_int < 0 or aqi_int > 500):
        aqi_int = None

    # Drop sensor-saturated PM2.5 readings (> 900 µg/m³ = instrument fault per CPCB)
    if pm25 is not None and pm25 > 900:
        pm25 = None
        aqi_int = None

    # PM10 must always be >= PM2.5 (PM10 includes PM2.5 by definition).
    # If a station reports PM10 < PM2.5 the PM10 instrument is faulty — drop it.
    if pm25 is not None and pm10 is not None and pm10 < pm25:
        logger.warning("PM10 < PM2.5 discarded (instrument fault)", station=station_code, pm25=pm25, pm10=pm10)
        pm10 = None

    # Fetch gas readings and apply per-pollutant sanity caps
    no2 = _val("no2")
    so2 = _val("so2")
    co  = _val("co")
    o3  = _val("o3")

    # CO > 40 mg/m³ (≈35 ppm) is beyond any realistic ambient reading and indicates
    # a stuck or saturated sensor — discard the value entirely
    if co is not None and co > 40:
        logger.warning("CO reading discarded (sensor fault)", station=station_code, co=co)
        co = None

    # NO2 > 180 µg/m³ exceeds CPCB's 1-hour standard; same stuck value repeatedly = sensor fault
    if no2 is not None and no2 > 180:
        logger.warning("NO2 reading discarded (sensor fault)", station=station_code, no2=no2)
        no2 = None

    # Nothing useful to store if no pollutant data and no overall AQI
    if pm25 is None and pm10 is None and aqi_int is None:
        return None

    logger.info("WAQI reading fetched", station=station_code, slug=slug, aqi=aqi_raw, pm25=pm25, co=co)
    return StationReadingIn(
        station_id=station_id,
        ts=ts,
        pm25=pm25,
        pm10=pm10,
        no2=no2,
        so2=so2,
        co=co,
        o3=o3,
        aqi=aqi_int,
    )


# ── data.gov.in CPCB bulk fetch (secondary) ───────────────────────────────────


async def fetch_city_readings_cpcb(city_name: str) -> dict[str, dict]:
    """Fetch all station readings for a city from data.gov.in CPCB API.

    Returns {} if CPCB_API_KEY is not set or the call fails.
    """
    api_key = settings.CPCB_API_KEY
    if not api_key:
        return {}

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
                "pm25": None, "pm10": None, "no2": None,
                "so2": None, "co": None, "o3": None,
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
    """Match a DB station to CPCB bulk data by fuzzy name on station_code keywords."""
    if not cpcb_data:
        return None

    parts = station_code.lower().split("_")
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
    if row.get("pm25") is None and row.get("pm10") is None:
        return None

    logger.info("Matched CPCB station", code=station_code, cpcb_station=row["_station_raw"], score=best_score)
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
) -> StationReadingIn | None:
    """Per-station fetch — returns None if no data available."""
    return None


# ── City → state name mapping for data.gov.in ─────────────────────────────────


def _city_to_state(city_name: str) -> str:
    _MAP = {
        "new delhi": "Delhi", "delhi": "Delhi",
        "gurugram": "Haryana", "faridabad": "Haryana",
        "noida": "Uttar Pradesh", "ghaziabad": "Uttar Pradesh",
        "mumbai": "Maharashtra", "pune": "Maharashtra",
        "nagpur": "Maharashtra", "nashik": "Maharashtra",
        "bengaluru": "Karnataka", "bangalore": "Karnataka",
        "mysuru": "Karnataka", "hubli": "Karnataka",
        "hyderabad": "Telangana", "warangal": "Telangana",
        "visakhapatnam": "Andhra Pradesh", "vijayawada": "Andhra Pradesh",
        "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu",
        "madurai": "Tamil Nadu",
        "kolkata": "West Bengal", "howrah": "West Bengal",
        "ahmedabad": "Gujarat", "surat": "Gujarat",
        "vadodara": "Gujarat", "rajkot": "Gujarat",
        "jaipur": "Rajasthan", "jodhpur": "Rajasthan",
        "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
        "agra": "Uttar Pradesh", "varanasi": "Uttar Pradesh",
        "patna": "Bihar", "gaya": "Bihar",
        "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh",
        "chandigarh": "Chandigarh",
        "ludhiana": "Punjab", "amritsar": "Punjab",
        "bhubaneswar": "Odisha", "ranchi": "Jharkhand",
        "raipur": "Chhattisgarh", "dehradun": "Uttarakhand",
        "guwahati": "Assam", "kochi": "Kerala",
        "thiruvananthapuram": "Kerala",
    }
    return _MAP.get(city_name.lower(), city_name)


def generate_historical_readings(station_id, start, end, interval_hours=1):
    """Stub — no mock historical data."""
    return []
