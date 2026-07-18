"""Reports & Export — Pydantic schemas."""

from pydantic import BaseModel


class CityInfo(BaseModel):
    id: str
    name: str
    state: str
    timezone: str


class AqiStats(BaseModel):
    current_avg_aqi: float | None
    peak_aqi_7d: float | None
    category_breakdown: dict[str, float]  # category → % hours


class EnforcementBrief(BaseModel):
    id: str
    source_name: str
    source_type: str
    priority_score: float
    status: str


class ForecastSummary(BaseModel):
    next_24h_peak_aqi: float | None
    dominant_hour: int | None  # 0-23 UTC hour with highest predicted AQI


class AttributionSummary(BaseModel):
    dominant_source: str | None
    breakdown: dict[str, float]  # source_type → %


class WardAqiRow(BaseModel):
    ward_id: str
    ward_name: str
    avg_aqi: float | None
    reading_count: int


class EnforcementStats(BaseModel):
    completed_period: int
    dispatched_active: int
    pending_count: int
    completed_total: int


class ReportSummaryOut(BaseModel):
    city: CityInfo
    period_days: int
    aqi_stats: AqiStats
    top_enforcement_items: list[EnforcementBrief]
    advisory_count_by_language: dict[str, int]
    forecast: ForecastSummary
    attribution: AttributionSummary
    ward_aqi_table: list[WardAqiRow]
    enforcement_stats: EnforcementStats
