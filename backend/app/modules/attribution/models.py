import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Attribution(Base):
    """Hourly source-contribution snapshot for a city, produced by the attribution engine."""

    __tablename__ = "attributions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aqi_at_computation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dominant_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicular_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    industrial_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    construction_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    agricultural_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    fire_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    other_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_dir: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AqiAlert(Base):
    """Alert record created when city AQI crosses a threshold (200 / 300 / 400)."""

    __tablename__ = "aqi_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    alert_level: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    aqi_value: Mapped[int] = mapped_column(Integer, nullable=False)
    station_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stations.id", ondelete="SET NULL"), nullable=True
    )
    dominant_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
