"""Advisory Engine API — Module 07."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.middleware import require_city_scope
from app.core.security import require_role
from app.modules.advisory import service
from app.modules.advisory.schemas import (
    AdvisoryGenerateResponse,
    AdvisoryListOut,
    AdvisoryOut,
)
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["advisory"])


@router.get(
    "/cities/{city_id}/advisories",
    response_model=ApiEnvelope[AdvisoryListOut],
)
async def list_advisories(
    city_id: str,
    language: str | None = Query(None, description="Filter by language code, e.g. 'en' or 'hi'"),
    channel: str | None = Query(None, description="Filter by channel: web|sms|push"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    items, total = await service.list_advisories(
        db, city_id, language=language, channel=channel, limit=limit, offset=offset
    )
    return ApiEnvelope(data=AdvisoryListOut(items=items, total=total))


@router.post(
    "/cities/{city_id}/advisories/generate",
    response_model=ApiEnvelope[AdvisoryGenerateResponse],
    status_code=201,
)
async def generate_advisories(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
    _role: dict = Depends(require_role("admin", "sysadmin")),
):
    """Generate fresh advisories for today for each supported language."""
    result = await service.generate_advisories(db, city_id)
    return ApiEnvelope(data=result)


@router.get(
    "/cities/{city_id}/advisories/{advisory_id}",
    response_model=ApiEnvelope[AdvisoryOut],
)
async def get_advisory(
    city_id: str,
    advisory_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    advisory = await service.get_advisory(db, advisory_id, city_id)
    if not advisory:
        raise NotFoundError(f"Advisory {advisory_id} not found")
    return ApiEnvelope(data=advisory)


@router.get(
    "/cities/{city_id}/advisory-count",
    response_model=ApiEnvelope[dict],
)
async def advisory_count(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    count = await service.count_advisories(db, city_id)
    return ApiEnvelope(data={"city_id": city_id, "total": count})
