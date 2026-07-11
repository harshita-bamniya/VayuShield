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

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# OSM tags → our emission source type
_TAG_RULES: list[tuple[str, str, str]] = [
    # (key, value, our_type)
    ("landuse", "industrial", "industrial"),
    ("landuse", "construction", "construction"),
    ("man_made", "works", "industrial"),
    ("man_made", "wastewater_plant", "industrial"),
    ("man_made", "chimney", "industrial"),
    ("power", "plant", "industrial"),
    ("power", "generator", "industrial"),
    ("amenity", "bus_station", "vehicular"),
    ("amenity", "fuel", "vehicular"),
    ("landuse", "landfill", "industrial"),
    ("landuse", "quarry", "industrial"),
    ("landuse", "farmland", "agricultural"),
    ("landuse", "farmyard", "agricultural"),
]


def _build_query(lat: float, lon: float, radius_m: int = 15000) -> str:
    """Build an Overpass QL query for emission-relevant features around a point."""
    tag_filters = "\n  ".join(
        f'node["{k}"="{v}"](around:{radius_m},{lat},{lon});'
        f'\n  way["{k}"="{v}"](around:{radius_m},{lat},{lon});'
        for k, v, _ in _TAG_RULES
    )
    return f"""
[out:json][timeout:25];
(
  {tag_filters}
);
out center tags;
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
    try:
        async with httpx.AsyncClient(timeout=40, headers=headers) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            if resp.status_code != 200:
                logger.warning("Overpass non-200", city=city_name, status=resp.status_code)
                return [], f"Overpass API returned HTTP {resp.status_code}"
            data = resp.json()
    except httpx.TimeoutException:
        logger.warning("Overpass timeout", city=city_name)
        return [], "Overpass API timed out — try again in a few seconds"
    except Exception as exc:
        logger.warning("Overpass API fetch failed", city=city_name, error=str(exc))
        return [], str(exc)

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
