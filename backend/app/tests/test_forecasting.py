"""Tests for Module 05: Forecasting Agent."""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.mark.asyncio
async def test_get_forecast_unauthenticated(client: AsyncClient):
    """Forecast endpoint requires authentication."""
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/forecast")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_forecast_runs_on_first_call(client: AsyncClient, sysadmin_token: str):
    """GET /forecast runs model on first call (no cached result) and returns 72 points."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/forecast",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["city_id"] == DELHI_CITY_ID
    assert data["horizon_hours"] == 72
    assert len(data["points"]) == 72


@pytest.mark.asyncio
async def test_forecast_points_have_required_fields(client: AsyncClient, sysadmin_token: str):
    """Every forecast point must have forecast_for_ts, predicted_aqi, model_version."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/forecast",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    data = resp.json()["data"]
    for pt in data["points"]:
        assert "forecast_for_ts" in pt
        assert "predicted_aqi" in pt
        assert "model_version" in pt
        assert 1 <= pt["predicted_aqi"] <= 500


@pytest.mark.asyncio
async def test_forecast_peak_aqi_is_max_of_points(client: AsyncClient, sysadmin_token: str):
    """peak_aqi in the envelope must equal max predicted_aqi across all points."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/forecast",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    data = resp.json()["data"]
    assert data["peak_aqi"] == max(pt["predicted_aqi"] for pt in data["points"])


@pytest.mark.asyncio
async def test_run_forecast_endpoint(client: AsyncClient, sysadmin_token: str):
    """POST /forecast/run triggers a fresh computation."""
    resp = await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/forecast/run",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["model_version"] == "diurnal-v1"
    assert len(data["points"]) == 72


@pytest.mark.asyncio
async def test_forecast_recompute_flag(client: AsyncClient, sysadmin_token: str):
    """GET /forecast?recompute=true produces a fresh result."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/forecast?recompute=true",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["horizon_hours"] == 72


@pytest.mark.asyncio
async def test_forecast_points_ordered_chronologically(client: AsyncClient, sysadmin_token: str):
    """Forecast points must be returned in ascending time order."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/forecast",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    points = resp.json()["data"]["points"]
    timestamps = [pt["forecast_for_ts"] for pt in points]
    assert timestamps == sorted(timestamps)
