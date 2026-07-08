"""auth: expand users table with full_name

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "full_name")
