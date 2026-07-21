"""satellite_observations table

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "satellite_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_date", sa.Date, nullable=False),
        sa.Column("aod_value", sa.Float, nullable=True),  # Aerosol Optical Depth 550nm
        sa.Column("estimated_pm25", sa.Float, nullable=True),  # AOD × 120 (µg/m³)
        sa.Column("source", sa.String(100), nullable=False, server_default="MODIS_TERRA"),
        sa.Column("is_mock", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_satobs_city_id", "satellite_observations", ["city_id"])
    op.create_index("ix_satobs_observed_date", "satellite_observations", ["observed_date"])
    op.create_index(
        "ix_satobs_city_date",
        "satellite_observations",
        ["city_id", "observed_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("satellite_observations")
