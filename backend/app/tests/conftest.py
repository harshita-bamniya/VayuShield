import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture
async def sysadmin_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vayushield.local", "password": "Admin@123"},
    )
    return resp.json()["data"]["access_token"]
