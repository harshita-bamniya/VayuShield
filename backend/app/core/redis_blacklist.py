"""JWT blacklist backed by Redis.

On logout: store the token's raw value in Redis with TTL = remaining token lifetime.
On every authenticated request: check Redis before trusting the token.
Falls back to an in-process set if Redis is unreachable (tokens revoked in that window
will not persist across restarts, but the API stays functional).
"""

import time
from typing import Any

from app.core.config import settings
from app.core.logging import logger

_BLACKLIST_PREFIX = "blacklist:"

_redis_client: Any = None
_redis_available: bool | None = None
_mem_blacklist: dict[str, float] = {}  # token -> expires_at (monotonic)


def _get_redis():
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("JWT blacklist: connected to Redis", url=settings.REDIS_URL)
    except Exception as exc:
        _redis_available = False
        logger.warning("JWT blacklist: Redis unavailable, using in-memory fallback", error=str(exc))
        return None
    return _redis_client


def blacklist_token(token: str, exp: int) -> None:
    """Add a token to the blacklist until its natural expiry."""
    now_unix = int(time.time())
    ttl = max(exp - now_unix, 1)
    r = _get_redis()
    if r is not None:
        try:
            r.setex(f"{_BLACKLIST_PREFIX}{token}", ttl, "1")
            return
        except Exception:
            pass
    _mem_blacklist[token] = time.monotonic() + ttl


def is_blacklisted(token: str) -> bool:
    """Return True if the token has been revoked."""
    r = _get_redis()
    if r is not None:
        try:
            return r.exists(f"{_BLACKLIST_PREFIX}{token}") == 1
        except Exception:
            pass
    entry = _mem_blacklist.get(token)
    if entry is None:
        return False
    if time.monotonic() < entry:
        return True
    _mem_blacklist.pop(token, None)
    return False
