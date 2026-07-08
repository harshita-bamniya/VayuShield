"""
Module 02 — City & Ward Core API tests.
Requires a running PostgreSQL+PostGIS database (run via docker-compose).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_cities_requires_sysadmin(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/cities")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_cities_as_sysadmin(client: AsyncClient, sysadmin_token: str) -> None:
    resp = await client.get(
        "/api/v1/cities",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert isinstance(body["data"], list)
    # Seed should have at least Delhi
    assert len(body["data"]) >= 1
    names = [c["name"] for c in body["data"]]
    assert "Delhi" in names


@pytest.mark.asyncio
async def test_create_and_get_city(client: AsyncClient, sysadmin_token: str) -> None:
    headers = {"Authorization": f"Bearer {sysadmin_token}"}
    payload = {"name": "Mumbai", "state": "Maharashtra", "timezone": "Asia/Kolkata"}
    resp = await client.post("/api/v1/cities", json=payload, headers=headers)
    assert resp.status_code == 201
    city = resp.json()["data"]
    assert city["name"] == "Mumbai"
    city_id = city["id"]

    resp2 = await client.get(f"/api/v1/cities/{city_id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["data"]["id"] == city_id


@pytest.mark.asyncio
async def test_list_wards_for_delhi(client: AsyncClient, sysadmin_token: str) -> None:
    headers = {"Authorization": f"Bearer {sysadmin_token}"}
    # Get Delhi id first
    resp = await client.get("/api/v1/cities", headers=headers)
    delhi = next(c for c in resp.json()["data"] if c["name"] == "Delhi")
    city_id = delhi["id"]

    resp2 = await client.get(f"/api/v1/cities/{city_id}/wards", headers=headers)
    assert resp2.status_code == 200
    wards = resp2.json()["data"]
    assert len(wards) >= 2
    ward_names = [w["name"] for w in wards]
    assert "Connaught Place" in ward_names
    assert "Dwarka" in ward_names


@pytest.mark.asyncio
async def test_list_stations_for_delhi(client: AsyncClient, sysadmin_token: str) -> None:
    headers = {"Authorization": f"Bearer {sysadmin_token}"}
    resp = await client.get("/api/v1/cities", headers=headers)
    delhi = next(c for c in resp.json()["data"] if c["name"] == "Delhi")
    city_id = delhi["id"]

    resp2 = await client.get(f"/api/v1/cities/{city_id}/stations", headers=headers)
    assert resp2.status_code == 200
    stations = resp2.json()["data"]
    assert len(stations) >= 2
    codes = [s["external_station_code"] for s in stations]
    assert "DPCC_ANAND_VIHAR" in codes
    assert "DPCC_ITO" in codes


@pytest.mark.asyncio
async def test_city_scope_blocks_wrong_city(client: AsyncClient) -> None:
    """An admin whose city_id doesn't match the path city_id gets 403."""
    # Create an admin user for a different city
    fake_city_id = "00000000-0000-0000-0000-000000000000"
    # Login as sysadmin to create the user
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vayushield.local", "password": "Admin@123"},
    )
    sysadmin_token = login_resp.json()["data"]["access_token"]
    headers_sys = {"Authorization": f"Bearer {sysadmin_token}"}

    # Create an admin for the fake city
    create_resp = await client.post(
        "/api/v1/users",
        json={
            "email": "city_admin_test@vayushield.local",
            "password": "Test@1234",
            "role": "admin",
            "city_id": fake_city_id,
            "full_name": "City Admin Test",
        },
        headers=headers_sys,
    )
    assert create_resp.status_code == 201

    # Login as that admin
    login2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "city_admin_test@vayushield.local", "password": "Test@1234"},
    )
    admin_token = login2.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Try to access Delhi (which has a different city_id) — should be 403
    delhi_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    resp = await client.get(f"/api/v1/cities/{delhi_id}/wards", headers=admin_headers)
    assert resp.status_code == 403
