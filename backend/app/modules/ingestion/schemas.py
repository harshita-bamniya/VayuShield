import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.schemas.geo import validate_geojson_geometry

# ── Station Readings ──────────────────────────────────────────────────────────


class StationReadingIn(BaseModel):
    """Payload from a CAAQMS connector — one reading per station per poll cycle."""

    station_id: str
    ts: datetime
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    so2: float | None = None
    co: float | None = None
    o3: float | None = None


class StationReadingOut(BaseModel):
    id: str
    station_id: str
    ts: datetime
    pm25: float | None
    pm10: float | None
    no2: float | None
    so2: float | None
    co: float | None
    o3: float | None
    aqi: int | None
    is_stale: bool
    # Derived field for API consumers
    aqi_category: str | None = None

    model_config = {"from_attributes": True}


class LatestReadingOut(BaseModel):
    """Latest reading for one station, with station metadata attached."""

    station_id: str
    station_name: str
    external_station_code: str
    ts: datetime | None
    pm25: float | None
    pm10: float | None
    aqi: int | None
    aqi_category: str | None
    is_stale: bool


# ── Weather ───────────────────────────────────────────────────────────────────


class WeatherReadingOut(BaseModel):
    id: str
    city_id: str
    ts: datetime
    wind_speed: float | None
    wind_dir: float | None
    humidity: float | None
    temp: float | None
    pressure: float | None

    model_config = {"from_attributes": True}


# ── Fire Hotspots ─────────────────────────────────────────────────────────────


class FireHotspotOut(BaseModel):
    id: str
    city_id: str
    detected_at: datetime
    geometry: dict[str, Any] | None
    confidence: float
    source: str
    frp: float | None

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


# ── Emission Sources ──────────────────────────────────────────────────────────


class EmissionSourceCreate(BaseModel):
    name: str
    type: str  # vehicular | industrial | construction | agricultural
    geometry: dict[str, Any] | None = None
    permit_status: str = "active"

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        valid = {"vehicular", "industrial", "construction", "agricultural"}
        if v not in valid:
            raise ValueError(f"type must be one of: {', '.join(sorted(valid))}")
        return v

    @field_validator("geometry")
    @classmethod
    def _validate_geometry(cls, v: Any) -> Any:
        return validate_geojson_geometry(v)


class EmissionSourceOut(BaseModel):
    id: str
    city_id: str
    name: str
    type: str
    geometry: dict[str, Any] | None
    permit_status: str
    last_inspected_at: datetime | None
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
