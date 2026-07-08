"""Shared GeoJSON geometry validator — imported by any module that accepts geometry input."""

import json
from typing import Any

VALID_GEOMETRY_TYPES = {
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
}


def validate_geojson_geometry(v: Any) -> Any:
    """Validate that a value is a GeoJSON geometry object (SRID 4326 assumed)."""
    if v is None:
        return None
    if not isinstance(v, dict):
        raise ValueError("Geometry must be a GeoJSON object (dict)")
    if v.get("type") not in VALID_GEOMETRY_TYPES:
        raise ValueError(f"geometry.type must be one of: {', '.join(sorted(VALID_GEOMETRY_TYPES))}")
    if "coordinates" not in v and v.get("type") != "GeometryCollection":
        raise ValueError("GeoJSON geometry must have a 'coordinates' field")
    return v


def geojson_to_wkt_expression(geojson: dict) -> str:
    """Return the ST_GeomFromGeoJSON SQL literal string for use in raw queries."""
    return json.dumps(geojson)
