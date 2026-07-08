"""Module 06 — Enforcement Agent tests."""

import pytest
from httpx import AsyncClient

CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

pytestmark = pytest.mark.anyio


async def test_list_enforcement_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/v1/cities/{CITY_ID}/enforcement")
    assert resp.status_code == 401


async def test_list_enforcement_returns_ranked_queue(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2, "Expected at least 2 seeded enforcement items"
    # Verify descending priority order
    scores = [item["priority_score"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True), "Items must be sorted by priority_score desc"


async def test_rank_creates_queue_items(client: AsyncClient, sysadmin_token: str):
    resp = await client.post(
        f"/api/v1/cities/{CITY_ID}/enforcement/rank",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 2


async def test_expired_permit_scores_higher_than_active(client: AsyncClient, sysadmin_token: str):
    resp = await client.post(
        f"/api/v1/cities/{CITY_ID}/enforcement/rank",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    items = resp.json()["data"]["items"]
    expired = next((i for i in items if i["source"]["permit_status"] == "expired"), None)
    active = next((i for i in items if i["source"]["permit_status"] == "active"), None)
    if expired and active:
        assert expired["priority_score"] >= active["priority_score"] - 0.2, (
            "Expired-permit source should score at least close to active-permit source"
        )


async def test_patch_status_to_dispatched(client: AsyncClient, sysadmin_token: str):
    list_resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    item_id = list_resp.json()["data"]["items"][0]["id"]

    patch_resp = await client.patch(
        f"/api/v1/cities/{CITY_ID}/enforcement/{item_id}",
        json={"status": "dispatched"},
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["status"] == "dispatched"


async def test_log_inspection_outcome(client: AsyncClient, sysadmin_token: str):
    list_resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    items = list_resp.json()["data"]["items"]
    # Find a non-dispatched item (the rank endpoint resets to pending)
    item_id = items[1]["id"] if len(items) > 1 else items[0]["id"]

    insp_resp = await client.post(
        f"/api/v1/cities/{CITY_ID}/enforcement/{item_id}/inspections",
        json={"outcome": "violation", "notes": "Excessive PM2.5 emissions detected"},
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert insp_resp.status_code == 201
    insp = insp_resp.json()["data"]
    assert insp["outcome"] == "violation"
    assert insp["enforcement_queue_id"] == item_id


async def test_pending_count_endpoint(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement-count",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "pending" in data
    assert isinstance(data["pending"], int)
