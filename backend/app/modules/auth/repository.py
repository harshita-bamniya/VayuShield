import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.auth.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    role: str = "admin",
    city_id: str | None = None,
    full_name: str | None = None,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(password),
        role=role,
        city_id=city_id,
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
