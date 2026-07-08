"""emission_sources table

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emission_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        # type: vehicular | industrial | construction | agricultural
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("permit_status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_emission_sources_city_id", "emission_sources", ["city_id"])
    op.create_index("ix_emission_sources_type", "emission_sources", ["type"])
    # PostGIS POINT geometry
    op.execute(
        sa.text(
            "SELECT AddGeometryColumn('public', 'emission_sources', 'geometry', 4326, 'POINT', 2)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_emission_sources_geometry ON emission_sources USING GIST (geometry)"
        )
    )


def downgrade() -> None:
    op.drop_table("emission_sources")
