"""cities table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("state", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False, server_default="Asia/Kolkata"),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cities_name", "cities", ["name"])


def downgrade() -> None:
    op.drop_table("cities")
