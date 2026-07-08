"""
Seed the database with a default sysadmin user on first boot.
This runs every startup but is idempotent — skips if admin already exists.
Module 01 will own the users table and password hashing; this stub uses
passlib directly so Module 00 can stand alone without depending on Module 01.
"""

import uuid

from passlib.context import CryptContext
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_admin() -> None:
    try:
        await _do_seed()
    except Exception as exc:
        logger.warning("Seed skipped (DB not ready yet)", error=str(exc))


async def _do_seed() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": settings.SEED_ADMIN_EMAIL},
        )
        if result.fetchone():
            logger.info("Seed admin already exists, skipping")
            return

        hashed = pwd_context.hash(settings.SEED_ADMIN_PASSWORD)
        await session.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
                VALUES (:id, :email, :password_hash, 'sysadmin', NOW(), NOW())
                """
            ),
            {"id": str(uuid.uuid4()), "email": settings.SEED_ADMIN_EMAIL, "password_hash": hashed},
        )
        await session.commit()
        logger.info("Seed admin created", email=settings.SEED_ADMIN_EMAIL)
