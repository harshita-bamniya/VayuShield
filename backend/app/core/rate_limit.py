"""Rate limiting — slowapi wrapper shared across all routers.

Uses Redis as the storage backend so limits persist across restarts and work
correctly under multiple workers. Falls back gracefully to in-memory if
settings.REDIS_URL is not set.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=settings.REDIS_URL or None,
)
