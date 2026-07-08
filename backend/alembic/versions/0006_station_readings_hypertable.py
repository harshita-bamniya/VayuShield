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
    # Promote to TimescaleDB hypertable — uses a SAVEPOINT so that if TimescaleDB is
    # not installed (e.g. plain PostGIS CI environment) the failure is rolled back to
    # the savepoint only, leaving the outer Alembic transaction healthy.
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT create_hypertable_sp"))
    try:
        conn.execute(
            sa.text(
                "SELECT create_hypertable('station_readings', 'ts', "
                "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
            )
        )
        conn.execute(sa.text("RELEASE SAVEPOINT create_hypertable_sp"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT create_hypertable_sp"))


def downgrade() -> None:
    op.drop_table("station_readings")
