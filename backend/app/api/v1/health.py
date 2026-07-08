from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import ApiEnvelope

router = APIRouter()


@router.get("/health", response_model=ApiEnvelope[dict])
async def health_check(db: AsyncSession = Depends(get_db)) -> ApiEnvelope[dict]:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    status = "ok" if db_ok else "degraded"
    return ApiEnvelope.ok({"status": status, "db": "ok" if db_ok else "error"})
