"""inspections table

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inspections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enforcement_queue_id",
            sa.String(36),
            sa.ForeignKey("enforcement_queue.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inspector_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),  # compliant | violation | no_access
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inspections_queue_id", "inspections", ["enforcement_queue_id"])
    op.create_index("ix_inspections_inspector_id", "inspections", ["inspector_id"])


def downgrade() -> None:
    op.drop_table("inspections")
