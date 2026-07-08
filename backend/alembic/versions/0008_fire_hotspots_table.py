"""fire_hotspots table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fire_hotspots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),  # 0-100
        sa.Column("source", sa.String(100), nullable=False, server_default="NASA_FIRMS"),
        sa.Column("frp", sa.Float, nullable=True),  # fire radiative power (MW)
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fire_hotspots_city_id", "fire_hotspots", ["city_id"])
    op.create_index("ix_fire_hotspots_detected_at", "fire_hotspots", ["detected_at"])
    # PostGIS POINT geometry
    op.execute(
        sa.text("SELECT AddGeometryColumn('public', 'fire_hotspots', 'geometry', 4326, 'POINT', 2)")
    )
    op.execute(
        sa.text("CREATE INDEX ix_fire_hotspots_geometry ON fire_hotspots USING GIST (geometry)")
    )


def downgrade() -> None:
    op.drop_table("fire_hotspots")
