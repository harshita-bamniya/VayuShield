import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Asia/Kolkata"
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Ward(Base):
    __tablename__ = "wards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # geometry stored as PostGIS MULTIPOLYGON — use Text here; actual PostGIS column
    # type is set by the Alembic migration via AddGeometryColumn.
    # Reads are done via ST_AsGeoJSON cast in the repository; inserts via ST_GeomFromGeoJSON.
    geometry: Mapped[str | None] = mapped_column(Text, nullable=True)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vulnerable_site_flags: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    ward_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wards.id", ondelete="SET NULL"), nullable=True
    )
    external_station_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # geometry stored as PostGIS POINT — same pattern as Ward.geometry
    geometry: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
