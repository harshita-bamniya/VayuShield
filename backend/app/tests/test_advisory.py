"""Tests for Module 07 — Advisory Engine."""

import pytest
from httpx import AsyncClient

DELHI_CITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.mark.anyio
async def test_list_advisories_unauthenticated(client: AsyncClient):
    resp = await client.get(f"/api/v1/cities/{DELHI_CITY_ID}/advisories")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_list_advisories_returns_list(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.anyio
async def test_generate_advisories_creates_per_language(client: AsyncClient, sysadmin_token: str):
    resp = await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories/generate",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "generated" in data
    assert "skipped" in data
    assert "advisories" in data
    # generated + skipped = number of languages we support
    assert data["generated"] + data["skipped"] == 2  # en + hi


@pytest.mark.anyio
async def test_generate_advisory_body_mentions_source(client: AsyncClient, sysadmin_token: str):
    # First generate (may be skipped if today's already exist)
    await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories/generate",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    # Then list and check body
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        params={"language": "en"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    # Body should mention some known source keyword
    body = items[0]["body"]
    source_keywords = ["vehicular", "industrial", "construction", "agricultural", "fire", "mixed"]
    assert any(kw in body.lower() for kw in source_keywords)


@pytest.mark.anyio
async def test_language_filter(client: AsyncClient, sysadmin_token: str):
    # Ensure advisories exist
    await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories/generate",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
        params={"language": "hi"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    # Every returned item must be in the requested language
    for item in items:
        assert item["language"] == "hi"


@pytest.mark.anyio
async def test_get_advisory_by_id(client: AsyncClient, sysadmin_token: str):
    # Generate to ensure at least one exists
    await client.post(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories/generate",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    # If all were skipped, list to get an id
    list_resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    items = list_resp.json()["data"]["items"]
    assert len(items) > 0
    advisory_id = items[0]["id"]

    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisories/{advisory_id}",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == advisory_id


@pytest.mark.anyio
async def test_generate_unauthenticated_returns_401(client: AsyncClient):
    resp = await client.post(f"/api/v1/cities/{DELHI_CITY_ID}/advisories/generate")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_advisory_count_endpoint(client: AsyncClient, sysadmin_token: str):
    resp = await client.get(
        f"/api/v1/cities/{DELHI_CITY_ID}/advisory-count",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total" in data
    assert isinstance(data["total"], int)
