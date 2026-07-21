import asyncio

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.seed import _do_seed
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def disable_rate_limits():
    """Disable slowapi rate limits for the entire test session.

    Tests call /auth/login repeatedly (once per test via sysadmin_token fixture).
    The 10/minute limit on that endpoint cascades into KeyError failures on every
    test that uses sysadmin_token once the counter trips.
    """
    from app.core.rate_limit import limiter

    limiter._enabled = False
    yield
    limiter._enabled = True


def _make_test_session() -> async_sessionmaker:
    """Create a test-scoped async engine with NullPool so connections don't
    carry event-loop affinity across tests."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def seed_db():
    """Run the seed once per test session via a dedicated event loop so that
    Delhi, stations, and ingestion data are present for all tests."""
    from app.core import database as db_module

    session_factory = _make_test_session()
    db_module.AsyncSessionLocal = session_factory

    asyncio.run(_do_seed())


@pytest.fixture
async def client(seed_db):  # noqa: ARG001
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
