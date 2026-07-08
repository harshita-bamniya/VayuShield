"""Tests for Module 04: Attribution Engine and AQI Alerts."""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.mark.asyncio
async def test_get_attribution_unauthenticated(client: AsyncClient):
    """Attribution endpoint requires authentication."""
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/attribution")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_attribution_returns_ranking(client: AsyncClient, sysadmin_token: str):
    """GET /attribution returns a ranked source breakdown."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/attribution",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["city_id"] == DELHI_CITY_ID
    assert "ranked_sources" in data
    assert isinstance(data["ranked_sources"], list)
    assert len(data["ranked_sources"]) > 0
    # Sources should be ranked 1, 2, 3, ...
    ranks = [s["rank"] for s in data["ranked_sources"]]
    assert ranks == list(range(1, len(ranks) + 1))
    # Dominant source must match rank-1 source
    assert data["dominant_source"] == data["ranked_sources"][0]["source_type"]


@pytest.mark.asyncio
async def test_trigger_attribution_compute(client: AsyncClient, sysadmin_token: str):
    """POST /attribution/compute runs engine and returns fresh result."""
    resp = await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/attribution/compute",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["city_id"] == DELHI_CITY_ID
    assert data["dominant_source"] is not None


@pytest.mark.asyncio
async def test_get_attribution_recompute_flag(client: AsyncClient, sysadmin_token: str):
    """GET /attribution?recompute=true returns fresh computation."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/attribution?recompute=true",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["computed_at"] is not None


@pytest.mark.asyncio
async def test_list_alerts_unauthenticated(client: AsyncClient):
    """Alerts endpoint requires authentication."""
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/alerts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_alerts_returns_seeded_data(client: AsyncClient, sysadmin_token: str):
    """GET /alerts returns the seeded alert history for Delhi."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/alerts",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    alerts = resp.json()["data"]
    assert isinstance(alerts, list)
    assert len(alerts) >= 3  # 3 seeded alerts

    levels = {a["alert_level"] for a in alerts}
    assert "poor" in levels


@pytest.mark.asyncio
async def test_list_alerts_active_only(client: AsyncClient, sysadmin_token: str):
    """?active_only=true returns only active alerts."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/alerts?active_only=true",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    alerts = resp.json()["data"]
    assert all(a["is_active"] for a in alerts)


@pytest.mark.asyncio
async def test_attribution_percentages_sum_to_100(client: AsyncClient, sysadmin_token: str):
    """Attribution breakdown percentages should sum to ~100%."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/attribution",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    total = sum(s["contribution_pct"] for s in data["ranked_sources"])
    assert abs(total - 100.0) < 1.0  # within 1% due to rounding
