import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    # 200 even when DB is unavailable (status field reflects actual state)
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["status"] in ("ok", "degraded")
