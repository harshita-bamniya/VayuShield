from datetime import datetime

from pydantic import BaseModel


class ForecastPointOut(BaseModel):
    id: str
    city_id: str
    ward_id: str | None = None
    generated_at: datetime
    forecast_for_ts: datetime
    predicted_aqi: int
    predicted_pm25: float | None = None
    confidence: float | None = None
    model_version: str
    is_stale: bool

    model_config = {"from_attributes": True}


class ForecastRunOut(BaseModel):
    city_id: str
    ward_id: str | None = None
    generated_at: datetime
    model_version: str
    horizon_hours: int
    points: list[ForecastPointOut]
    peak_aqi: int
    peak_at: datetime
    is_stale: bool = False
