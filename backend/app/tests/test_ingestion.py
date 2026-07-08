"""
Module 03 — Ingestion API tests.
Requires running PostgreSQL+PostGIS+TimescaleDB (docker-compose up).
"""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.mark.asyncio
async def test_latest_readings_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/readings/latest")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_latest_readings_for_delhi(client: AsyncClient, sysadmin_token: str) -> None:
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/readings/latest",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    stations = body["data"]
    assert len(stations) >= 2
    codes = [s["external_station_code"] for s in stations]
    assert "DPCC_ANAND_VIHAR" in codes
    assert "DPCC_ITO" in codes
    # Seeded readings should populate aqi
    for s in stations:
        assert s["aqi"] is not None
        assert s["aqi_category"] is not None


@pytest.mark.asyncio
async def test_station_readings_history(client: AsyncClient, sysadmin_token: str) -> None:
    STATION_AV_ID = "d4e5f6a7-b8c9-0123-def0-123456789013"
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/stations/{STATION_AV_ID}/readings",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        params={"limit": 24},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert len(body["data"]) > 0
    assert body["meta"]["total"] > 0


@pytest.mark.asyncio
async def test_latest_weather(client: AsyncClient, sysadmin_token: str) -> None:
    # Weather is not seeded (requires live Open-Meteo call in poll) — just check endpoint responds
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/weather/latest",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200  # data may be None if weather hasn't been polled yet


@pytest.mark.asyncio
async def test_list_emission_sources(client: AsyncClient, sysadmin_token: str) -> None:
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/emission-sources",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert len(body["data"]) >= 4
    types = {s["type"] for s in body["data"]}
    assert "vehicular" in types
    assert "industrial" in types


@pytest.mark.asyncio
async def test_create_emission_source(client: AsyncClient, sysadmin_token: str) -> None:
    payload = {
        "name": "Test Factory",
        "type": "industrial",
        "geometry": {"type": "Point", "coordinates": [77.25, 28.65]},
        "permit_status": "active",
    }
    resp = await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/emission-sources",
        json=payload,
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["name"] == "Test Factory"
    assert body["data"]["geometry"]["type"] == "Point"


@pytest.mark.asyncio
async def test_aqi_computation() -> None:
    from app.core.aqi import aqi_category, compute_aqi, pm25_to_aqi

    assert pm25_to_aqi(0) == 0
    assert pm25_to_aqi(30) == 50
    assert pm25_to_aqi(90) == 200
    assert pm25_to_aqi(120) == 300
    assert compute_aqi(75.0) == 150  # Moderate band
    assert aqi_category(45) == "Good"
    assert aqi_category(150) == "Moderate"
    assert aqi_category(350) == "Very Poor"
