"""Open-Meteo weather connector (free, no API key required).

Fetches hourly wind speed, wind direction, relative humidity, temperature,
and surface pressure for a given lat/lon. Used by the weather polling job.

Open-Meteo API docs: https://open-meteo.com/en/docs
"""

from datetime import datetime, timedelta, timezone

import httpx

from app.core.logging import logger

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Delhi coordinates (pilot city)
DELHI_LAT = 28.6139
DELHI_LON = 77.2090


async def fetch_weather(
    lat: float,
    lon: float,
    city_id: str,
    hours_back: int = 24,
) -> list[dict]:
    """Fetch hourly weather data from Open-Meteo for the past `hours_back` hours.

    Returns a list of dicts ready for bulk_insert_weather().
    """
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(hours=hours_back)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "windspeed_10m,winddirection_10m,relativehumidity_2m,temperature_2m,surface_pressure",
        "wind_speed_unit": "ms",
        "timezone": "UTC",
        "start_date": start_date,
        "end_date": end_date,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    wind_speeds = hourly.get("windspeed_10m", [])
    wind_dirs = hourly.get("winddirection_10m", [])
    humidity = hourly.get("relativehumidity_2m", [])
    temps = hourly.get("temperature_2m", [])
    pressures = hourly.get("surface_pressure", [])

    readings = []
    for i, ts_str in enumerate(times):
        ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
        if ts > now:
            continue
        readings.append(
            {
                "city_id": city_id,
                "ts": ts,
                "wind_speed": wind_speeds[i] if i < len(wind_speeds) else None,
                "wind_dir": wind_dirs[i] if i < len(wind_dirs) else None,
                "humidity": humidity[i] if i < len(humidity) else None,
                "temp": temps[i] if i < len(temps) else None,
                "pressure": pressures[i] if i < len(pressures) else None,
            }
        )

    logger.info(
        "Weather data fetched",
        city_id=city_id,
        count=len(readings),
        source="open-meteo",
    )
    return readings


async def fetch_weather_for_delhi(city_id: str, hours_back: int = 24) -> list[dict]:
    return await fetch_weather(DELHI_LAT, DELHI_LON, city_id, hours_back)
