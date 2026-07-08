"""Auth endpoint tests — run with: pytest app/tests/test_auth.py"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "admin@vayushield.local", "password": "Admin@123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert body["data"]["user"]["email"] == "admin@vayushield.local"
    assert body["data"]["user"]["role"] == "sysadmin"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "admin@vayushield.local", "password": "wrong"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_valid_token(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login", json={"email": "admin@vayushield.local", "password": "Admin@123"}
    )
    token = login.json()["data"]["access_token"]
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "admin@vayushield.local"


@pytest.mark.asyncio
async def test_require_sysadmin_blocks_admin_role(client: AsyncClient):
    # Create a token with role=admin (not sysadmin) — no real user needed for role check
    token = create_access_token(
        {"sub": "fake-id", "email": "admin@test.com", "role": "admin", "city_id": None}
    )
    resp = await client.post(
        "/api/v1/users",
        json={"email": "x@x.com", "password": "p"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
