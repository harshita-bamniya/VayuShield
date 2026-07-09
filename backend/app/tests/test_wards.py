"""Tests for Module 08 — Ward Detail & Map Overlay."""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
WARD_CP_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
WARD_DWARKA_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.anyio
async def test_list_wards_unauthenticated(client: AsyncClient):
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/wards")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_list_wards_includes_avg_aqi(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    wards = resp.json()["data"]
    assert isinstance(wards, list)
    assert len(wards) >= 2
    # Every ward should have the new AQI enrichment fields
    for ward in wards:
        assert "avg_aqi" in ward
        assert "aqi_category" in ward
        assert "geometry" in ward


@pytest.mark.anyio
async def test_get_ward_detail_structure(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards/{WARD_CP_ID}",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    ward = resp.json()["data"]
    assert ward["id"] == WARD_CP_ID
    assert ward["city_id"] == DELHI_CITY_ID
    assert "avg_aqi" in ward
    assert "aqi_category" in ward
    assert "station_readings" in ward
    assert isinstance(ward["station_readings"], list)
    assert "attribution_breakdown" in ward
    assert "dominant_source" in ward
    assert "advisory_count" in ward
    assert isinstance(ward["advisory_count"], int)


@pytest.mark.anyio
async def test_get_ward_detail_not_found(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards/{NONEXISTENT_ID}",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_ward_detail_station_readings_have_aqi_category(
    client: AsyncClient, sysadmin_token: str
):
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards/{WARD_CP_ID}",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    ward = resp.json()["data"]
    for reading in ward["station_readings"]:
        # Each reading with an AQI should have an aqi_category
        if reading.get("aqi") is not None:
            assert reading["aqi_category"] is not None
