"""NASA MODIS MAIAC AOD connector.

Fetches daily Aerosol Optical Depth (AOD at 550nm) from NASA LAADS DAAC
for a city bounding box, then converts to estimated surface PM2.5.

API: NASA LAADS DAAC — https://ladsweb.modaps.eosdis.nasa.gov/
Auth: Bearer token from https://earthdata.nasa.gov/ (EARTHDATA_TOKEN in .env)

Falls back to a realistic mock observation when no token is set, so the
rest of the pipeline (DB insert, frontend card) works without credentials.

PM2.5 conversion: PM2.5 ≈ AOD × 120  (simplified WHO/WMO empirical formula)
"""

import hashlib
import uuid
from datetime import UTC, date, datetime

import httpx

from app.core.config import settings
from app.core.logging import logger

# NASA LAADS DAAC — MODIS Terra Collection 6.1 daily L3 global AOD product
LAADS_BASE = "https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/allData/61/MOD08_D3"

# Typical urban AOD baseline by known city names (used for mock generation)
_CITY_AOD_BASELINE: dict[str, float] = {
    "Delhi": 0.62,
    "Mumbai": 0.44,
    "Bengaluru": 0.28,
    "Chennai": 0.35,
    "Kolkata": 0.52,
    "Hyderabad": 0.31,
    "Pune": 0.33,
}
_DEFAULT_BASELINE = 0.40


def _mock_aod(city_name: str, obs_date: date) -> float:
    """Deterministic mock AOD — stable per city+date, varies ±15%."""
    baseline = _CITY_AOD_BASELINE.get(city_name, _DEFAULT_BASELINE)
    # Use a hash of (city, date) for repeatable variance
    seed = int(hashlib.md5(f"{city_name}{obs_date.isoformat()}".encode()).hexdigest(), 16)
    variance = ((seed % 1000) / 1000 - 0.5) * 0.30  # ±15% of range
    return round(max(0.05, min(1.5, baseline + variance * baseline)), 3)


async def fetch_satellite_aod(
    city_id: str,
    city_name: str,
    lat: float,
    lon: float,
    obs_date: date | None = None,
) -> dict:
    """Return a single satellite observation dict ready for DB insert.

    Keys: city_id, observed_date, aod_value, estimated_pm25, source, is_mock
    """
    obs_date = obs_date or datetime.now(UTC).date()
    token = getattr(settings, "EARTHDATA_TOKEN", "")

    if not token:
        logger.info("EARTHDATA_TOKEN not set — using mock satellite AOD", city_name=city_name)
        return _build_mock_obs(city_id, city_name, obs_date)

    try:
        return await _fetch_real_aod(city_id, obs_date, lat, lon, token)
    except Exception as exc:
        logger.warning("NASA LAADS fetch failed — falling back to mock", error=str(exc), city=city_name)
        return _build_mock_obs(city_id, city_name, obs_date)


def _build_mock_obs(city_id: str, city_name: str, obs_date: date) -> dict:
    aod = _mock_aod(city_name, obs_date)
    return {
        "id": str(uuid.uuid4()),
        "city_id": city_id,
        "observed_date": obs_date,
        "aod_value": aod,
        "estimated_pm25": round(aod * 120, 1),
        "source": "MODIS_TERRA",
        "is_mock": True,
    }


async def _fetch_real_aod(city_id: str, obs_date: date, lat: float, lon: float, token: str) -> dict:
    """Fetch MODIS Terra MOD08_D3 daily global AOD product from NASA LAADS."""
    year = obs_date.year
    doy = obs_date.timetuple().tm_yday  # day-of-year for LAADS path

    # LAADS DAAC file listing for the given day
    listing_url = f"{LAADS_BASE}/{year}/{doy:03d}.json"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(listing_url, headers=headers)
        resp.raise_for_status()
        files = resp.json()

    # Pick global file (MOD08_D3 is one file per day worldwide)
    if not files:
        raise ValueError(f"No MODIS MOD08_D3 files found for {obs_date}")

    file_name = files[0]["name"]
    download_url = f"{LAADS_BASE}/{year}/{doy:03d}/{file_name}"

    # The HDF4 file requires special parsing; we extract via NASA subsetting service instead
    # NASA OPeNDAP / Giovanni subsetting for a point
    subset_url = (
        f"https://giovanni.gsfc.nasa.gov/giovanni/daac-bin/service_manager.pl"
        f"?service=ArAvTs&starttime={obs_date.isoformat()}T00:00:00Z"
        f"&endtime={obs_date.isoformat()}T23:59:59Z"
        f"&bbox={lon - 0.5},{lat - 0.5},{lon + 0.5},{lat + 0.5}"
        f"&data=MOD08_D3_6_1_AOD_550_Dark_Target_Deep_Blue_Combined"
        f"&format=json"
    )
    resp2 = await client.get(subset_url, headers=headers, timeout=60)
    resp2.raise_for_status()
    data = resp2.json()

    # Parse response — Giovanni returns a list of time-value pairs
    values = [v for item in data.get("data", []) for v in item.get("values", []) if v is not None]
    if not values:
        raise ValueError("No AOD values in Giovanni response")

    aod = round(float(sum(values) / len(values)), 3)
    return {
        "id": str(uuid.uuid4()),
        "city_id": city_id,
        "observed_date": obs_date,
        "aod_value": aod,
        "estimated_pm25": round(aod * 120, 1),
        "source": "MODIS_TERRA",
        "is_mock": False,
    }


def aod_to_pm25(aod: float) -> float:
    """Convert AOD at 550nm to estimated surface PM2.5 (µg/m³)."""
    return round(aod * 120, 1)


def aod_category(aod: float | None) -> str:
    if aod is None:
        return "Unknown"
    if aod < 0.2:
        return "Low"
    if aod < 0.4:
        return "Moderate"
    if aod < 0.6:
        return "High"
    return "Very High"
