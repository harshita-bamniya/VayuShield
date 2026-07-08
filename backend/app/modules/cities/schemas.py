import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.schemas.geo import validate_geojson_geometry

# ── City ─────────────────────────────────────────────────────────────────────


class CityCreate(BaseModel):
    name: str
    state: str
    timezone: str = "Asia/Kolkata"
    config_json: dict[str, Any] = {}


class CityOut(BaseModel):
    id: str
    name: str
    state: str
    timezone: str
    config_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Ward ─────────────────────────────────────────────────────────────────────


class WardCreate(BaseModel):
    name: str
    geometry: dict[str, Any] | None = None
    population: int | None = None
    vulnerable_site_flags: dict[str, Any] = {}

    @field_validator("geometry")
    @classmethod
    def _validate_geometry(cls, v: Any) -> Any:
        return validate_geojson_geometry(v)


class WardOut(BaseModel):
    id: str
    city_id: str
    name: str
    geometry: dict[str, Any] | None = None
    population: int | None
    vulnerable_site_flags: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("geometry", mode="before")
    @classmethod
    def _parse_geometry(cls, v: Any) -> Any:
        """geometry arrives as a JSON string from ST_AsGeoJSON — parse it."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v


# ── Station ──────────────────────────────────────────────────────────────────


class StationCreate(BaseModel):
    ward_id: str | None = None
    external_station_code: str
    name: str
    geometry: dict[str, Any] | None = None
    is_active: bool = True

    @field_validator("geometry")
    @classmethod
    def _validate_geometry(cls, v: Any) -> Any:
        return validate_geojson_geometry(v)


class StationOut(BaseModel):
    id: str
    city_id: str
    ward_id: str | None
    external_station_code: str
    name: str
    geometry: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("geometry", mode="before")
    @classmethod
    def _parse_geometry(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v
