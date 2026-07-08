"""Module 05: forecasts table — 72-hour AQI/PM2.5 forecast points per city.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecasts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id", sa.String(36), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_for_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_aqi", sa.Integer, nullable=False),
        sa.Column("predicted_pm25", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="diurnal-v1"),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forecasts_city_id_generated_at", "forecasts", ["city_id", "generated_at"])
    op.create_index(
        "ix_forecasts_city_id_forecast_for_ts", "forecasts", ["city_id", "forecast_for_ts"]
    )


def downgrade() -> None:
    op.drop_index("ix_forecasts_city_id_forecast_for_ts", "forecasts")
    op.drop_index("ix_forecasts_city_id_generated_at", "forecasts")
    op.drop_table("forecasts")
