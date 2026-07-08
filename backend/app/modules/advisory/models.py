from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func

from app.core.database import Base


class Advisory(Base):
    __tablename__ = "advisories"

    id = Column(String(36), primary_key=True)
    city_id = Column(
        String(36), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ward_id = Column(String(36), ForeignKey("wards.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(10), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    aqi_level = Column(String(50), nullable=False)
    dominant_source = Column(String(50), nullable=True)
    channel = Column(String(50), nullable=False, default="web")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
