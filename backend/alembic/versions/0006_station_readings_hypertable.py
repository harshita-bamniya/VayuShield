"""station_readings TimescaleDB hypertable

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "station_readings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "station_id",
            sa.String(36),
            sa.ForeignKey("stations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # ts is the hypertable time dimension — must NOT be nullable
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pm25", sa.Float, nullable=True),
        sa.Column("pm10", sa.Float, nullable=True),
        sa.Column("no2", sa.Float, nullable=True),
        sa.Column("so2", sa.Float, nullable=True),
        sa.Column("co", sa.Float, nullable=True),
        sa.Column("o3", sa.Float, nullable=True),
        sa.Column("aqi", sa.Integer, nullable=True),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id", "ts"),  # composite PK required by TimescaleDB
    )
    op.create_index("ix_station_readings_station_id", "station_readings", ["station_id"])
    op.create_index("ix_station_readings_ts", "station_readings", ["ts"])
    # Promote to TimescaleDB hypertable partitioned by ts (chunk_time_interval = 1 day)
    op.execute(
        sa.text(
            "SELECT create_hypertable('station_readings', 'ts', "
            "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
        )
    )


def downgrade() -> None:
    op.drop_table("station_readings")
