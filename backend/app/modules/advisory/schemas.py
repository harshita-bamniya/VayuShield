from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdvisoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    city_id: str
    ward_id: str | None = None
    language: str
    title: str
    body: str
    aqi_level: str
    dominant_source: str | None = None
    channel: str
    sent_at: datetime | None = None
    created_at: datetime


class AdvisoryListOut(BaseModel):
    items: list[AdvisoryOut]
    total: int


class AdvisoryGenerateResponse(BaseModel):
    generated: int
    skipped: int
    advisories: list[AdvisoryOut]
