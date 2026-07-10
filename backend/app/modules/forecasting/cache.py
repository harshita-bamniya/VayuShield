"""Forecast cache — Redis with in-memory fallback.

Stores serialized ForecastRunOut JSON for CACHE_TTL_SECONDS per city_id.
Falls back to a process-local dict if Redis is unavailable.
"""

import json
import time
from typing import Any

from app.core.config import settings
from app.core.logging import logger

CACHE_TTL_SECONDS = 3600  # 1 hour
_CACHE_KEY_PREFIX = "forecast:"

# In-memory fallback: {key: (expires_at, payload_json)}
_mem_cache: dict[str, tuple[float, str]] = {}

_redis_client: Any = None
_redis_available: bool | None = None  # None = untested


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
        logger.info("Forecast cache: connected to Redis", url=settings.REDIS_URL)
    except Exception as exc:
        _redis_available = False
        logger.warning("Forecast cache: Redis unavailable, using in-memory fallback", error=str(exc))
        return None
    return _redis_client


def _key(city_id: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{city_id}"


def get_cached(city_id: str) -> str | None:
    """Return cached forecast JSON string, or None if missing/expired."""
    r = _get_redis()
    if r is not None:
        try:
            return r.get(_key(city_id))
        except Exception:
            pass  # fall through to mem cache

    entry = _mem_cache.get(_key(city_id))
    if entry and time.monotonic() < entry[0]:
        return entry[1]
    return None


def set_cached(city_id: str, payload: dict) -> None:
    """Serialize and cache the forecast payload."""
    raw = json.dumps(payload, default=str)
    r = _get_redis()
    if r is not None:
        try:
            r.setex(_key(city_id), CACHE_TTL_SECONDS, raw)
            return
        except Exception:
            pass  # fall through to mem cache

    _mem_cache[_key(city_id)] = (time.monotonic() + CACHE_TTL_SECONDS, raw)


def invalidate(city_id: str) -> None:
    """Remove cached forecast for a city (called before fresh recompute)."""
    r = _get_redis()
    if r is not None:
        try:
            r.delete(_key(city_id))
        except Exception:
            pass
    _mem_cache.pop(_key(city_id), None)
