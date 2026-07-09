"""
Module 11 — City Onboarding Admin tests.
Requires a running PostgreSQL+PostGIS database (run via docker-compose).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_city(client: AsyncClient, sysadmin_token: str) -> None:
    """POST /cities creates a city and returns it with expected fields."""
    headers = {"Authorization": f"Bearer {sysadmin_token}"}
    payload = {
        "name": "Bengaluru",
        "state": "Karnataka",
        "timezone": "Asia/Kolkata",
        "config_json": {"pilot": True},
    }
    resp = await client.post("/api/v1/cities", json=payload, headers=headers)
    assert resp.status_code == 201
    city = resp.json()["data"]
    assert city["name"] == "Bengaluru"
    assert city["state"] == "Karnataka"
    assert city["timezone"] == "Asia/Kolkata"
    assert city["config_json"] == {"pilot": True}
    assert "id" in city
    assert "created_at" in city


@pytest.mark.asyncio
async def test_create_ward_with_geometry(client: AsyncClient, sysadmin_token: str) -> None:
    """POST /cities/{id}/wards creates a ward with GeoJSON geometry."""
    headers = {"Authorization": f"Bearer {sysadmin_token}"}

    # Create a city to add a ward to
    city_resp = await client.post(
        "/api/v1/cities",
        json={"name": "TestCityWard", "state": "TestState", "timezone": "Asia/Kolkata"},
        headers=headers,
    )
    assert city_resp.status_code == 201
    city_id = city_resp.json()["data"]["id"]

    geometry = {
        "type": "MultiPolygon",
        "coordinates": [[[[77.2, 28.6], [77.3, 28.6], [77.3, 28.7], [77.2, 28.7], [77.2, 28.6]]]],
    }
    ward_resp = await client.post(
        f"/api/v1/cities/{city_id}/wards",
        json={"name": "Test Ward", "population": 250000, "geometry": geometry},
        headers=headers,
    )
    assert ward_resp.status_code == 201
    ward = ward_resp.json()["data"]
    assert ward["name"] == "Test Ward"
    assert ward["population"] == 250000
    assert ward["city_id"] == city_id
    # Geometry round-trips as a dict (deserialized from ST_AsGeoJSON)
    assert ward["geometry"] is not None
    assert ward["geometry"]["type"] == "MultiPolygon"


@pytest.mark.asyncio
async def test_create_station(client: AsyncClient, sysadmin_token: str) -> None:
    """POST /cities/{id}/stations creates a station with a Point geometry."""
    headers = {"Authorization": f"Bearer {sysadmin_token}"}

    # Create a city
    city_resp = await client.post(
        "/api/v1/cities",
        json={"name": "TestCityStation", "state": "TestState2", "timezone": "Asia/Kolkata"},
        headers=headers,
    )
    assert city_resp.status_code == 201
    city_id = city_resp.json()["data"]["id"]

    geometry = {"type": "Point", "coordinates": [77.5946, 12.9716]}
    station_resp = await client.post(
        f"/api/v1/cities/{city_id}/stations",
        json={
            "name": "Bengaluru Central CAAQMS",
            "external_station_code": "KSPCB_CENTRAL",
            "geometry": geometry,
            "is_active": True,
        },
        headers=headers,
    )
    assert station_resp.status_code == 201
    station = station_resp.json()["data"]
    assert station["name"] == "Bengaluru Central CAAQMS"
    assert station["external_station_code"] == "KSPCB_CENTRAL"
    assert station["city_id"] == city_id
    assert station["is_active"] is True
    assert station["geometry"] is not None
    assert station["geometry"]["type"] == "Point"
    coords = station["geometry"]["coordinates"]
    assert abs(coords[0] - 77.5946) < 0.001
    assert abs(coords[1] - 12.9716) < 0.001


@pytest.mark.asyncio
async def test_create_city_missing_fields(client: AsyncClient, sysadmin_token: str) -> None:
    """POST /cities without required fields returns 422."""
    headers = {"Authorization": f"Bearer {sysadmin_token}"}
    resp = await client.post("/api/v1/cities", json={"name": "OnlyName"}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_ward_invalid_geometry(client: AsyncClient, sysadmin_token: str) -> None:
    """POST /cities/{id}/wards with a bad geometry type returns 422."""
    headers = {"Authorization": f"Bearer {sysadmin_token}"}

    city_resp = await client.post(
        "/api/v1/cities",
        json={"name": "TestCityBadGeo", "state": "TestState3", "timezone": "Asia/Kolkata"},
        headers=headers,
    )
    city_id = city_resp.json()["data"]["id"]

    bad_geometry = {"type": "InvalidType", "coordinates": []}
    resp = await client.post(
        f"/api/v1/cities/{city_id}/wards",
        json={"name": "Bad Ward", "geometry": bad_geometry},
        headers=headers,
    )
    assert resp.status_code == 422
