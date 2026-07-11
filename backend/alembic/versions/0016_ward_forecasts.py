"""Add ward_id to forecasts for hyperlocal ward-level predictions

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("forecasts", sa.Column("ward_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "forecasts_ward_id_fkey",
        "forecasts",
        "wards",
        ["ward_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_forecasts_ward_id_forecast_for_ts",
        "forecasts",
        ["ward_id", "forecast_for_ts"],
    )


def downgrade() -> None:
    op.drop_index("ix_forecasts_ward_id_forecast_for_ts", table_name="forecasts")
    op.drop_constraint("forecasts_ward_id_fkey", "forecasts", type_="foreignkey")
    op.drop_column("forecasts", "ward_id")
