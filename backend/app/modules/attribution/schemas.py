from datetime import datetime

from pydantic import BaseModel


class SourceBreakdown(BaseModel):
    vehicular_pct: float | None = None
    industrial_pct: float | None = None
    construction_pct: float | None = None
    agricultural_pct: float | None = None
    fire_pct: float | None = None
    other_pct: float | None = None


class AttributionOut(BaseModel):
    id: str
    city_id: str
    computed_at: datetime
    aqi_at_computation: int | None = None
    dominant_source: str | None = None
    breakdown: SourceBreakdown
    wind_speed: float | None = None
    wind_dir: float | None = None
    source_count: int | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RankedSource(BaseModel):
    source_type: str
    contribution_pct: float
    rank: int


class AttributionRankingOut(BaseModel):
    city_id: str
    computed_at: datetime
    aqi: int | None
    dominant_source: str | None
    ranked_sources: list[RankedSource]
    wind_speed: float | None
    wind_dir: float | None
    wind_description: str | None
    confidence_score: float | None = None
    pollutant_snapshot: dict | None = None


class AqiAlertOut(BaseModel):
    id: str
    city_id: str
    alert_level: str
    threshold: int
    aqi_value: int
    station_id: str | None = None
    dominant_source: str | None = None
    triggered_at: datetime
    resolved_at: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
