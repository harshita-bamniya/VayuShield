import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StationReading(Base):
    """15-minute AQI/pollutant readings from CAAQMS stations.

    TimescaleDB hypertable partitioned by ts. Composite PK (id, ts) required by TimescaleDB.
    """

    __tablename__ = "station_readings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    station_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    o3: Mapped[float | None] = mapped_column(Float, nullable=True)
    aqi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class WeatherReading(Base):
    """Hourly weather readings (wind, humidity, temp) from Open-Meteo or other source.

    TimescaleDB hypertable partitioned by ts.
    """

    __tablename__ = "weather_readings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)   # m/s
    wind_dir: Mapped[float | None] = mapped_column(Float, nullable=True)     # degrees
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)     # %
    temp: Mapped[float | None] = mapped_column(Float, nullable=True)         # °C
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)     # hPa


class FireHotspot(Base):
    """Active fire detections from NASA FIRMS within city bounding-box."""

    __tablename__ = "fire_hotspots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    geometry: Mapped[str | None] = mapped_column(Text, nullable=True)  # PostGIS POINT
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, server_default="NASA_FIRMS")
    frp: Mapped[float | None] = mapped_column(Float, nullable=True)    # fire radiative power (MW)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmissionSource(Base):
    """Known pollution-emitting sites (factories, construction zones, etc.)."""

    __tablename__ = "emission_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    city_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # SOURCE_CATEGORIES
    geometry: Mapped[str | None] = mapped_column(Text, nullable=True)  # PostGIS POINT
    permit_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="active"
    )  # active | expired | pending
    last_inspected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
