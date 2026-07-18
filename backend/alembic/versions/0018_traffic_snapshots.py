"""traffic_snapshots table

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traffic_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("segment_id", sa.String(100), nullable=False),
        sa.Column("segment_name", sa.String(255), nullable=True),
        sa.Column("congestion_ratio", sa.Float, nullable=False),   # current/free-flow speed ratio (>1 = congested)
        sa.Column("current_speed", sa.Float, nullable=True),       # km/h
        sa.Column("free_flow_speed", sa.Float, nullable=True),     # km/h
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lon", sa.Float, nullable=True),
        sa.Column("is_mock", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_traffic_city_id", "traffic_snapshots", ["city_id"])
    op.create_index("ix_traffic_ts", "traffic_snapshots", ["ts"])
    op.create_index("ix_traffic_city_ts", "traffic_snapshots", ["city_id", "ts"])


def downgrade() -> None:
    op.drop_table("traffic_snapshots")
