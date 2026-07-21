import asyncio
import inspect

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
    """Bypass slowapi rate limiting for the entire test session.

    Setting _enabled = False is supposed to short-circuit the middleware, but
    the @limiter.limit() decorator may call _check_request_limit independently
    of the middleware's _enabled check (observed with Redis-backed storage).
    Patching _check_request_limit to a no-op guarantees no code path enforces
    limits regardless of slowapi version.
    """
    from app.core.rate_limit import limiter

    limiter._enabled = False
    original_check = limiter._check_request_limit

    if inspect.iscoroutinefunction(original_check):

        async def _noop(*args, **kwargs):
            return None

    else:

        def _noop(*args, **kwargs):
            return None

    limiter._check_request_limit = _noop
    yield
    limiter._check_request_limit = original_check
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


@pytest.fixture(scope="session")
def sysadmin_token(seed_db) -> str:
    """Obtain a sysadmin JWT once per session by calling authenticate_user
    directly — never hits the HTTP layer so the 10/minute login rate limit
    is never consumed."""
    from app.core import database as db_module
    from app.modules.auth.service import authenticate_user, issue_tokens

    async def _get() -> str:
        async with db_module.AsyncSessionLocal() as db:
            user = await authenticate_user(db, "admin@vayushield.local", "Admin@123")
        return issue_tokens(user).access_token

    return asyncio.run(_get())


@pytest.fixture
async def client(seed_db):  # noqa: ARG001
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
