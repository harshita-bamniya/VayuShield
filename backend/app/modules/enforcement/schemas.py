from datetime import datetime

from pydantic import BaseModel


class EmissionSourceBrief(BaseModel):
    id: str
    name: str
    type: str
    permit_status: str
    last_inspected_at: datetime | None = None

    model_config = {"from_attributes": True}


class EnforcementItemOut(BaseModel):
    id: str
    city_id: str
    emission_source_id: str
    priority_score: float
    evidence_brief_text: str | None = None
    status: str
    attribution_id: str | None = None
    forecast_id: str | None = None
    created_at: datetime
    updated_at: datetime
    source: EmissionSourceBrief | None = None

    model_config = {"from_attributes": True}


class EnforcementListOut(BaseModel):
    items: list[EnforcementItemOut]
    total: int


class EnforcementStatusUpdate(BaseModel):
    status: str  # pending | dispatched | completed


class InspectionCreate(BaseModel):
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    outcome: str | None = None  # compliant | violation | no_access
    notes: str | None = None


class InspectionOut(BaseModel):
    id: str
    enforcement_queue_id: str
    inspector_id: str | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    outcome: str | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
