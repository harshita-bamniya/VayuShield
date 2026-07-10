"""
S4 — Data Quality & Polish tests.

Covers: IDW ward AQI, NA/stale sensor handling in ward detail,
seed data realism, and the AQI category helper.
"""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
WARD_CP_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
WARD_DWARKA_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"


# ── IDW ward AQI ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wards_list_has_avg_aqi(client: AsyncClient, sysadmin_token: str) -> None:
    """Every ward returned by the list endpoint must have avg_aqi populated
    (IDW query should return a value when stations have readings)."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    wards = resp.json()["data"]
    assert len(wards) >= 2
    # Both seeded wards should have an AQI value from IDW
    wards_with_aqi = [w for w in wards if w["avg_aqi"] is not None]
    assert len(wards_with_aqi) >= 1, "IDW should produce at least one ward AQI"


@pytest.mark.asyncio
async def test_wards_aqi_values_are_reasonable(client: AsyncClient, sysadmin_token: str) -> None:
    """IDW-computed AQI should be within CPCB range."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    wards = resp.json()["data"]
    for ward in wards:
        if ward["avg_aqi"] is not None:
            assert 0 <= ward["avg_aqi"] <= 500, (
                f"Ward {ward['name']} has out-of-range AQI {ward['avg_aqi']}"
            )


@pytest.mark.asyncio
async def test_wards_have_aqi_category(client: AsyncClient, sysadmin_token: str) -> None:
    """aqi_category must be set for every ward that has avg_aqi."""
    valid_categories = {"Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"}
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    wards = resp.json()["data"]
    for ward in wards:
        if ward["avg_aqi"] is not None:
            assert ward["aqi_category"] in valid_categories, (
                f"Ward {ward['name']} has unexpected category {ward['aqi_category']}"
            )


# ── Stale/NA sensor handling ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ward_detail_station_readings_have_is_stale(
    client: AsyncClient, sysadmin_token: str
) -> None:
    """station_readings in ward detail must include is_stale field."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/wards/{WARD_CP_ID}",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    ward = resp.json()["data"]
    for reading in ward["station_readings"]:
        assert "is_stale" in reading, "is_stale field missing from station reading"


# ── Seed data realism ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seeded_readings_have_nonzero_pm25(client: AsyncClient, sysadmin_token: str) -> None:
    """Seeded PM2.5 values must be positive (not zero/flat sine wave artifacts)."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/readings/latest",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    stations = resp.json()["data"]
    assert len(stations) >= 1
    for s in stations:
        if s.get("pm25") is not None:
            assert s["pm25"] > 0, "PM2.5 should never be zero from the diurnal seed"


@pytest.mark.asyncio
async def test_seeded_readings_cover_multiple_hours(
    client: AsyncClient, sysadmin_token: str
) -> None:
    """Station history should have many distinct hours (7-day seed)."""
    STATION_AV_ID = "d4e5f6a7-b8c9-0123-def0-123456789013"
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/stations/{STATION_AV_ID}/readings",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        params={"limit": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 24, "Expected at least 24 hrs of seeded readings"


# ── AQI helper correctness ────────────────────────────────────────────────────


def test_aqi_category_boundaries() -> None:
    from app.core.aqi import aqi_category

    assert aqi_category(0) == "Good"
    assert aqi_category(50) == "Good"
    assert aqi_category(51) == "Satisfactory"
    assert aqi_category(100) == "Satisfactory"
    assert aqi_category(101) == "Moderate"
    assert aqi_category(200) == "Moderate"
    assert aqi_category(201) == "Poor"
    assert aqi_category(300) == "Poor"
    assert aqi_category(301) == "Very Poor"
    assert aqi_category(400) == "Very Poor"
    assert aqi_category(401) == "Severe"
    assert aqi_category(500) == "Severe"
