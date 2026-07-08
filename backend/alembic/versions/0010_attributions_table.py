"""Module 04: attributions table — per-city hourly source attribution snapshots.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attributions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id", sa.String(36), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aqi_at_computation", sa.Integer, nullable=True),
        sa.Column("dominant_source", sa.String(50), nullable=True),
        sa.Column("vehicular_pct", sa.Float, nullable=True),
        sa.Column("industrial_pct", sa.Float, nullable=True),
        sa.Column("construction_pct", sa.Float, nullable=True),
        sa.Column("agricultural_pct", sa.Float, nullable=True),
        sa.Column("fire_pct", sa.Float, nullable=True),
        sa.Column("other_pct", sa.Float, nullable=True),
        sa.Column("wind_speed", sa.Float, nullable=True),
        sa.Column("wind_dir", sa.Float, nullable=True),
        sa.Column("source_count", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_attributions_city_id_computed_at", "attributions", ["city_id", "computed_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_attributions_city_id_computed_at", "attributions")
    op.drop_table("attributions")
