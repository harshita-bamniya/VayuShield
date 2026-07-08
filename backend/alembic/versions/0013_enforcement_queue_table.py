"""enforcement_queue table

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enforcement_queue",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id", sa.String(36), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "emission_source_id",
            sa.String(36),
            sa.ForeignKey("emission_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("priority_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence_brief_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "attribution_id",
            sa.String(36),
            sa.ForeignKey("attributions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "forecast_id",
            sa.String(36),
            sa.ForeignKey("forecasts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_enforcement_queue_city_id", "enforcement_queue", ["city_id"])
    op.create_index(
        "ix_enforcement_queue_score", "enforcement_queue", ["city_id", "priority_score"]
    )
    op.create_index("ix_enforcement_queue_status", "enforcement_queue", ["city_id", "status"])


def downgrade() -> None:
    op.drop_table("enforcement_queue")
