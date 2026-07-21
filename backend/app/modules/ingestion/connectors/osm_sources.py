"""OpenStreetMap Overpass API connector — auto-discover emission sources near a city.

Queries for real-world features known to contribute to air pollution:
  - Industrial areas / factories
  - Construction sites
  - Bus depots / transport hubs
  - Power plants
  - Landfills / waste sites

No API key required. Rate-limit: 1 request per second (handled by caller).
"""

import httpx

from app.core.logging import logger

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# OSM tags → our emission source type (trimmed to highest-signal tags only)
_TAG_RULES: list[tuple[str, str, str]] = [
    ("landuse", "industrial", "industrial"),
    ("landuse", "construction", "construction"),
    ("man_made", "works", "industrial"),
    ("power", "plant", "industrial"),
    ("amenity", "bus_station", "vehicular"),
    ("landuse", "landfill", "industrial"),
    ("landuse", "quarry", "industrial"),
]


def _build_query(lat: float, lon: float, radius_m: int = 15000) -> str:
    """Build a compact Overpass QL query using a union of way filters only."""
    tag_filters = "\n  ".join(
        f'way["{k}"="{v}"](around:{radius_m},{lat},{lon});' for k, v, _ in _TAG_RULES
    )
    return f"""
[out:json][timeout:30];
(
  {tag_filters}
);
out center tags 50;
"""


def _osm_type(tags: dict) -> str:
    for key, val, src_type in _TAG_RULES:
        if tags.get(key) == val:
            return src_type
    return "industrial"


def _osm_name(tags: dict, fallback: str) -> str:
    return tags.get("name") or tags.get("operator") or tags.get("brand") or fallback


async def fetch_emission_sources(
    lat: float, lon: float, city_name: str, radius_m: int = 20000, limit: int = 20
) -> tuple[list[dict], str | None]:
    """Return (sources, error_msg). sources is a list of dicts ready for create_emission_source.

    Each dict has: name, type, geometry (GeoJSON Point), permit_status.
    Returns ([], error_message) on failure.
    """
    query = _build_query(lat, lon, radius_m)
    headers = {
        "User-Agent": "VayuShield-AI/1.0 (air quality monitoring platform)",
        "Accept": "application/json",
    }
    data = None
    last_error = "Overpass API unavailable — try again later"
    async with httpx.AsyncClient(timeout=35, headers=headers) as client:
        for url in OVERPASS_URLS:
            try:
                resp = await client.post(url, data={"data": query})
                if resp.status_code == 200:
                    data = resp.json()
                    break
                last_error = f"Overpass API returned HTTP {resp.status_code}"
                logger.warning("Overpass non-200", city=city_name, url=url, status=resp.status_code)
            except httpx.TimeoutException:
                last_error = "Overpass API timed out — try again in a few seconds"
                logger.warning("Overpass timeout", city=city_name, url=url)
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Overpass fetch failed", city=city_name, url=url, error=str(exc))

    if data is None:
        return [], last_error

    elements = data.get("elements", [])
    seen_names: set[str] = set()
    results: list[dict] = []

    for el in elements:
        tags = el.get("tags", {})
        src_type = _osm_type(tags)

        # Skip agricultural sources unless clearly a burning / storage site
        if src_type == "agricultural" and not any(
            kw in tags.get("name", "").lower()
            for kw in ("burn", "stubble", "fire", "storage", "silo")
        ):
            continue

        # Get coordinates (nodes have lat/lon; ways have center)
        if el["type"] == "node":
            elat, elon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            elat, elon = center.get("lat"), center.get("lon")

        if elat is None or elon is None:
            continue

        name = _osm_name(
            tags,
            fallback=f"{city_name} {src_type.title()} Site",
        )

        # De-duplicate by name
        if name in seen_names:
            continue
        seen_names.add(name)

        results.append(
            {
                "name": name,
                "type": src_type,
                "geometry": {"type": "Point", "coordinates": [elon, elat]},
                "permit_status": "active",
            }
        )

        if len(results) >= limit:
            break

    logger.info(
        "OSM emission sources discovered",
        city=city_name,
        found=len(results),
    )
    return results, None
