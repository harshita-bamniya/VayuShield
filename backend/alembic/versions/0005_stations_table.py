"""stations table with PostGIS geometry

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ward_id",
            sa.String(36),
            sa.ForeignKey("wards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_station_code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stations_city_id", "stations", ["city_id"])
    op.create_index("ix_stations_ward_id", "stations", ["ward_id"])
    op.create_index(
        "ix_stations_external_code", "stations", ["external_station_code"], unique=True
    )
    # PostGIS geometry column — POINT, WGS84 (SRID 4326)
    op.execute(
        sa.text(
            "SELECT AddGeometryColumn('public', 'stations', 'geometry', 4326, 'POINT', 2)"
        )
    )
    op.execute(sa.text("CREATE INDEX ix_stations_geometry ON stations USING GIST (geometry)"))


def downgrade() -> None:
    op.drop_table("stations")
