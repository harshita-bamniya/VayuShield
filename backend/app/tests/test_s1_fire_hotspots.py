"""
S1 — Fire Hotspots Map tests.

Verifies the fire-hotspots endpoint that feeds the orange/red CircleMarkers
on the dashboard map. No live NASA FIRMS call is needed — the endpoint is
structurally tested against a seeded DB.
"""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_fire_hotspots_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/fire-hotspots")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_fire_hotspots_returns_list(client: AsyncClient, sysadmin_token: str) -> None:
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/fire-hotspots",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_fire_hotspots_item_shape(client: AsyncClient, sysadmin_token: str) -> None:
    """Each hotspot dict must carry the fields the map layer needs."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/fire-hotspots",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    for item in items:
        assert "id" in item
        assert "lat" in item
        assert "lon" in item
        assert "confidence" in item
        assert "frp" in item
        assert "detected_at" in item


@pytest.mark.asyncio
async def test_fire_hotspots_hours_back_param(client: AsyncClient, sysadmin_token: str) -> None:
    """hours_back query param is accepted; response is still a list."""
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/fire-hotspots",
        params={"hours_back": 48},
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_fire_hotspots_unknown_city_returns_404(
    client: AsyncClient, sysadmin_token: str
) -> None:
    """Unknown city_id returns 404 from the city scope check."""
    resp = await client.get(
        f"/api/v1/cities/{NONEXISTENT_ID}/fire-hotspots",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 404
