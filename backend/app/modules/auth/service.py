from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.modules.auth.models import User
from app.modules.auth.repository import get_user_by_email
from app.modules.auth.schemas import TokenResponse, UserOut


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    return user


def issue_tokens(user: User) -> TokenResponse:
    payload = {"sub": user.id, "email": user.email, "role": user.role, "city_id": user.city_id}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        user=UserOut.model_validate(user),
    )
