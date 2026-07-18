from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {**data, "exp": expire, "type": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {**data, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str, check_blacklist: bool = True) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")
    if check_blacklist:
        from app.core.redis_blacklist import is_blacklisted  # late import avoids circular dep

        if is_blacklisted(token):
            raise UnauthorizedError("Token has been revoked")
    return payload


def require_role(*roles: str):
    """FastAPI dependency — checks Bearer token and asserts role membership."""

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> dict:
        if not credentials:
            raise UnauthorizedError("Authentication required")
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedError("Access token required")
        if payload.get("role") not in roles:
            raise ForbiddenError(f"Role must be one of: {', '.join(roles)}")
        return payload

    return dependency


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Dependency — any authenticated user; returns token payload."""
    if not credentials:
        raise UnauthorizedError("Authentication required")
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedError("Access token required")
    return payload
