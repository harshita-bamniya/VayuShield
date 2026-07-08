"""weather_readings TimescaleDB hypertable

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weather_readings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "city_id",
            sa.String(36),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wind_speed", sa.Float, nullable=True),  # m/s
        sa.Column("wind_dir", sa.Float, nullable=True),  # degrees (0-360)
        sa.Column("humidity", sa.Float, nullable=True),  # %
        sa.Column("temp", sa.Float, nullable=True),  # °C
        sa.Column("pressure", sa.Float, nullable=True),  # hPa
        sa.PrimaryKeyConstraint("id", "ts"),
    )
    op.create_index("ix_weather_readings_city_id", "weather_readings", ["city_id"])
    op.create_index("ix_weather_readings_ts", "weather_readings", ["ts"])
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT create_hypertable_sp"))
    try:
        conn.execute(
            sa.text(
                "SELECT create_hypertable('weather_readings', 'ts', "
                "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
            )
        )
        conn.execute(sa.text("RELEASE SAVEPOINT create_hypertable_sp"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT create_hypertable_sp"))


def downgrade() -> None:
    op.drop_table("weather_readings")
