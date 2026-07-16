"""
Loads real municipal ward boundaries from Datameet GeoJSON files.
Source: https://github.com/datameet/Municipal_Spatial_Data (CC BY-SA 2.5 India)
"""

import json
from pathlib import Path

_GEODATA_DIR = Path(__file__).parent / "geodata"


def _load(filename: str) -> list[dict]:
    path = _GEODATA_DIR / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("features", [])


def _geom_json(feature: dict) -> str:
    return json.dumps(feature["geometry"])


# ── Per-city ward extractors ──────────────────────────────────────────────────

def delhi_wards() -> list[dict]:
    """290 MCD wards. Props: Ward_Name, Ward_No."""
    return [
        {"name": f["properties"]["Ward_Name"].title(), "geometry": _geom_json(f)}
        for f in _load("delhi_wards.geojson")
        if f.get("geometry") and f["properties"].get("Ward_Name")
    ]


def mumbai_wards() -> list[dict]:
    """24 BMC administrative wards. Props: name (A–T + suburbs)."""
    return [
        {"name": f"Ward {f['properties']['name']}", "geometry": _geom_json(f)}
        for f in _load("mumbai_wards.geojson")
        if f.get("geometry") and f["properties"].get("name")
    ]


def bengaluru_wards() -> list[dict]:
    """243 BBMP wards (2022 delimitation). Props: KGISWardName, KGISWardNo."""
    return [
        {"name": f["properties"]["KGISWardName"].title(), "geometry": _geom_json(f)}
        for f in _load("bengaluru_wards.geojson")
        if f.get("geometry") and f["properties"].get("KGISWardName")
    ]


def hyderabad_wards() -> list[dict]:
    """145 GHMC wards. Props: name."""
    return [
        {"name": f["properties"]["name"].title(), "geometry": _geom_json(f)}
        for f in _load("hyderabad_wards.geojson")
        if f.get("geometry") and f["properties"].get("name")
    ]


def chennai_wards() -> list[dict]:
    """201 GCC wards. Props: Ward_No, Zone_Name (no ward name field)."""
    return [
        {
            "name": f"Ward {f['properties']['Ward_No']} ({f['properties'].get('Zone_Name', '').title()})",
            "geometry": _geom_json(f),
        }
        for f in _load("chennai_wards.geojson")
        if f.get("geometry") and f["properties"].get("Ward_No")
    ]


def kolkata_wards() -> list[dict]:
    """141 KMC wards. Props: WARD (ward number)."""
    return [
        {"name": f"Ward {f['properties']['WARD']}", "geometry": _geom_json(f)}
        for f in _load("kolkata_wards.geojson")
        if f.get("geometry") and f["properties"].get("WARD")
    ]


def pune_wards() -> list[dict]:
    """58 PMC electoral wards (2022). Props: Name1 (Marathi), wardnum."""
    return [
        {
            "name": (
                f["properties"].get("Name1")
                or f"Ward {f['properties'].get('wardnum', '')}"
            ).strip(),
            "geometry": _geom_json(f),
        }
        for f in _load("pune_wards.geojson")
        if f.get("geometry")
    ]


CITY_WARD_LOADERS: dict[str, callable] = {
    "Delhi":     delhi_wards,
    "Mumbai":    mumbai_wards,
    "Bengaluru": bengaluru_wards,
    "Hyderabad": hyderabad_wards,
    "Chennai":   chennai_wards,
    "Kolkata":   kolkata_wards,
    "Pune":      pune_wards,
}
