"""Module 04: aqi_alerts table — alert history for threshold crossings.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aqi_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("city_id", sa.String(36), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_level", sa.String(20), nullable=False),   # "poor" | "very_poor" | "severe"
        sa.Column("threshold", sa.Integer, nullable=False),         # 200 | 300 | 400
        sa.Column("aqi_value", sa.Integer, nullable=False),         # observed AQI that triggered
        sa.Column("station_id", sa.String(36), sa.ForeignKey("stations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dominant_source", sa.String(50), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_aqi_alerts_city_id_triggered_at", "aqi_alerts", ["city_id", "triggered_at"])
    op.create_index("ix_aqi_alerts_city_id_is_active", "aqi_alerts", ["city_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_aqi_alerts_city_id_is_active", "aqi_alerts")
    op.drop_index("ix_aqi_alerts_city_id_triggered_at", "aqi_alerts")
    op.drop_table("aqi_alerts")
