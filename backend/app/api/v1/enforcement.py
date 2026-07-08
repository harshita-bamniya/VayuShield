"""Enforcement Agent API — Module 06."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.middleware import require_city_scope
from app.core.security import require_role
from app.modules.enforcement import repository as repo
from app.modules.enforcement import service
from app.modules.enforcement.schemas import (
    EnforcementItemOut,
    EnforcementListOut,
    EnforcementStatusUpdate,
    InspectionCreate,
    InspectionOut,
)
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["enforcement"])


@router.get(
    "/cities/{city_id}/enforcement",
    response_model=ApiEnvelope[EnforcementListOut],
)
async def list_enforcement_queue(
    city_id: str,
    status: str | None = Query(None, description="Filter by status: pending|dispatched|completed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    result = await service.get_queue(db, city_id, status=status, limit=limit, offset=offset)
    return ApiEnvelope(data=result)


@router.post(
    "/cities/{city_id}/enforcement/rank",
    response_model=ApiEnvelope[EnforcementListOut],
)
async def rank_enforcement_queue(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
    _role: dict = Depends(require_role("admin", "sysadmin")),
):
    """Re-score all emission sources and rebuild the enforcement queue."""
    result = await service.rank_queue(db, city_id)
    return ApiEnvelope(data=result)


@router.get(
    "/cities/{city_id}/enforcement/{item_id}",
    response_model=ApiEnvelope[EnforcementItemOut],
)
async def get_enforcement_item(
    city_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    item = await service.get_item(db, item_id, city_id)
    if not item:
        raise NotFoundError(f"Enforcement item {item_id} not found")
    return ApiEnvelope(data=item)


@router.patch(
    "/cities/{city_id}/enforcement/{item_id}",
    response_model=ApiEnvelope[dict],
)
async def update_enforcement_status(
    city_id: str,
    item_id: str,
    body: EnforcementStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    valid = {"pending", "dispatched", "completed"}
    if body.status not in valid:
        raise ValueError(f"status must be one of {valid}")
    updated = await service.update_status(db, item_id, body.status)
    if not updated:
        raise NotFoundError(f"Enforcement item {item_id} not found")
    return ApiEnvelope(data={"id": item_id, "status": body.status})


@router.post(
    "/cities/{city_id}/enforcement/{item_id}/inspections",
    response_model=ApiEnvelope[InspectionOut],
    status_code=201,
)
async def log_inspection(
    city_id: str,
    item_id: str,
    body: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    caller: dict = Depends(require_city_scope),
):
    item = await service.get_item(db, item_id, city_id)
    if not item:
        raise NotFoundError(f"Enforcement item {item_id} not found")

    inspector_id = caller.get("sub")
    insp = await repo.create_inspection(
        db,
        queue_item_id=item_id,
        inspector_id=inspector_id,
        data=body.model_dump(exclude_none=True),
    )
    return ApiEnvelope(data=InspectionOut.model_validate(insp))


@router.get(
    "/cities/{city_id}/enforcement-count",
    response_model=ApiEnvelope[dict],
)
async def pending_count(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    count = await service.count_pending(db, city_id)
    return ApiEnvelope(data={"city_id": city_id, "pending": count})
