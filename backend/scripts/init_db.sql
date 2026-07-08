-- Run once by Docker on first container start.
-- Enables PostGIS + TimescaleDB extensions.
-- Alembic migrations own all table DDL; this file only enables extensions.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
