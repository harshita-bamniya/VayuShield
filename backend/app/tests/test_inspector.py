"""Module 10 — Inspector PWA tests."""

import pytest
from httpx import AsyncClient

CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

pytestmark = pytest.mark.anyio


@pytest.fixture
async def inspector_token(client: AsyncClient, sysadmin_token: str) -> str:
    """Create an inspector user and return their JWT."""
    create_resp = await client.post(
        "/api/v1/users",
        json={
            "email": "inspector@vayushield.local",
            "password": "Inspect@123",
            "role": "inspector",
            "city_id": CITY_ID,
            "full_name": "Field Inspector",
        },
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    # 201 on first run, 400 on duplicate — either way we can login
    assert create_resp.status_code in (201, 400)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@vayushield.local", "password": "Inspect@123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["data"]["access_token"]


async def test_inspector_can_list_enforcement_queue(client: AsyncClient, inspector_token: str):
    """Inspector role must be able to read the enforcement queue for their city."""
    resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


async def test_inspector_can_submit_inspection(client: AsyncClient, inspector_token: str):
    """Inspector can POST an inspection with a valid outcome."""
    # Fetch any queue item
    list_resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    items = list_resp.json()["data"]["items"]
    assert items, "Need at least one seeded enforcement item"
    item_id = items[0]["id"]

    insp_resp = await client.post(
        f"/api/v1/cities/{CITY_ID}/enforcement/{item_id}/inspections",
        json={"outcome": "passed", "notes": "Site visit complete — emissions within limits."},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert insp_resp.status_code == 201
    insp = insp_resp.json()["data"]
    assert insp["outcome"] == "passed"
    assert insp["enforcement_queue_id"] == item_id


async def test_invalid_outcome_rejected(client: AsyncClient, inspector_token: str):
    """Submitting an unknown outcome value must return 422."""
    list_resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    item_id = list_resp.json()["data"]["items"][0]["id"]

    bad_resp = await client.post(
        f"/api/v1/cities/{CITY_ID}/enforcement/{item_id}/inspections",
        json={"outcome": "not_a_real_outcome"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert bad_resp.status_code == 422


async def test_inspector_cannot_access_foreign_city(client: AsyncClient, inspector_token: str):
    """Inspector scoped to CITY_ID must receive 403 for a different city."""
    other_city = "00000000-0000-0000-0000-000000000099"
    resp = await client.get(
        f"/api/v1/cities/{other_city}/enforcement",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 403


async def test_inspector_can_mark_item_completed(client: AsyncClient, inspector_token: str):
    """After submitting inspection, inspector can patch status to completed."""
    list_resp = await client.get(
        f"/api/v1/cities/{CITY_ID}/enforcement",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    item_id = list_resp.json()["data"]["items"][0]["id"]

    patch_resp = await client.patch(
        f"/api/v1/cities/{CITY_ID}/enforcement/{item_id}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["status"] == "completed"
