"""wards table with PostGIS geometry

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("population", sa.Integer, nullable=True),
        sa.Column(
            "vulnerable_site_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wards_city_id", "wards", ["city_id"])
    # PostGIS geometry column — MULTIPOLYGON, WGS84 (SRID 4326)
    op.execute(
        sa.text(
            "SELECT AddGeometryColumn('public', 'wards', 'geometry', 4326, 'MULTIPOLYGON', 2)"
        )
    )
    op.execute(sa.text("CREATE INDEX ix_wards_geometry ON wards USING GIST (geometry)"))


def downgrade() -> None:
    op.drop_table("wards")
