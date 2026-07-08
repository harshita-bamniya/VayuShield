import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EnforcementQueueItem(Base):
    __tablename__ = "enforcement_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    emission_source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("emission_sources.id", ondelete="CASCADE"), nullable=False
    )
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_brief_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attribution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("attributions.id", ondelete="SET NULL"), nullable=True
    )
    forecast_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("forecasts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    enforcement_queue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enforcement_queue.id", ondelete="CASCADE"), nullable=False
    )
    inspector_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
