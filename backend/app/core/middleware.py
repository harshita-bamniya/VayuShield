"""Shared FastAPI dependencies for cross-cutting concerns (city scoping, etc.)."""

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.core.security import get_current_user


def require_city_scope(city_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency: verifies the caller's JWT city_id matches the path city_id.

    Sysadmins bypass the check and can access any city.
    Returns the token payload so the caller can inspect role/city_id if needed.
    """
    if current_user.get("role") == "sysadmin":
        return current_user
    user_city_id = current_user.get("city_id")
    if not user_city_id or user_city_id != city_id:
        raise ForbiddenError("You do not have access to this city")
    return current_user
