"""advisories table

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advisories",
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
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("aqi_level", sa.String(50), nullable=False),
        sa.Column("dominant_source", sa.String(50), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False, server_default="web"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_advisories_city_id", "advisories", ["city_id"])
    op.create_index("ix_advisories_city_language", "advisories", ["city_id", "language"])
    op.create_index("ix_advisories_created_at", "advisories", ["created_at"])


def downgrade() -> None:
    op.drop_table("advisories")
