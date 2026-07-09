"""Module 12 — Reports & Export tests."""

import pytest
from httpx import AsyncClient

CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

pytestmark = pytest.mark.anyio


async def test_summary_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/v1/cities/{CITY_ID}/reports/summary")
    assert resp.status_code == 401


async def test_summary_structure(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/reports/summary",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Top-level keys
    assert "city" in data
    assert "aqi_stats" in data
    assert "top_enforcement_items" in data
    assert "advisory_count_by_language" in data
    assert "forecast" in data
    assert "attribution" in data
    assert "ward_aqi_table" in data
    # City sub-keys
    city = data["city"]
    assert city["name"] == "Delhi"
    assert "state" in city
    assert "timezone" in city
    # AQI stats sub-keys
    aqi = data["aqi_stats"]
    assert "current_avg_aqi" in aqi
    assert "peak_aqi_7d" in aqi
    assert "category_breakdown" in aqi
    # Top enforcement — at most 3 items
    assert len(data["top_enforcement_items"]) <= 3
    # Ward table is a list
    assert isinstance(data["ward_aqi_table"], list)


async def test_csv_content_type(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/reports/summary.csv",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    # CSV must have at least the header row and city_name row
    lines = resp.text.strip().splitlines()
    assert lines[0] == "stat_key,value"
    assert any(line.startswith("city_name,") for line in lines)


async def test_ward_aqi_table_content(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/reports/summary",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        params={"days": 7},
    )
    assert resp.status_code == 200
    ward_rows = resp.json()["data"]["ward_aqi_table"]
    assert isinstance(ward_rows, list)
    for row in ward_rows:
        assert "ward_id" in row
        assert "ward_name" in row
        assert "reading_count" in row


async def test_summary_days_param(client: AsyncClient, sysadmin_token: str):
    """Verify the days query param is accepted for 7 / 30 / 90."""
    for days in (7, 30, 90):
        resp = await client.get(
            f"/api/v1/cities/{CITY_ID}/reports/summary",
            headers={"Authorization": f"Bearer {sysadmin_token}"},
            params={"days": days},
        )
        assert resp.status_code == 200, f"days={days} failed"
        assert resp.json()["data"]["period_days"] == days
