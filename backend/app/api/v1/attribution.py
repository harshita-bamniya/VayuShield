"""Attribution Engine API — Module 04."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import require_city_scope
from app.modules.attribution import repository as repo
from app.modules.attribution import service
from app.modules.attribution.schemas import AqiAlertOut, AttributionRankingOut
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["attribution"])


@router.get(
    "/cities/{city_id}/attribution",
    response_model=ApiEnvelope[AttributionRankingOut],
)
async def get_attribution(
    city_id: str,
    recompute: bool = Query(False, description="Trigger a fresh computation before returning"),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Return the latest AQI source attribution for a city.

    Pass `?recompute=true` to force a fresh run of the attribution engine.
    """
    if recompute:
        result = await service.compute_attribution(db, city_id)
        return ApiEnvelope(data=result)

    result = await service.get_latest_attribution_ranking(db, city_id)
    if result is None:
        result = await service.compute_attribution(db, city_id)
    return ApiEnvelope(data=result)


@router.post(
    "/cities/{city_id}/attribution/compute",
    response_model=ApiEnvelope[AttributionRankingOut],
)
async def trigger_attribution(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Manually trigger an attribution computation and persist the result."""
    result = await service.compute_attribution(db, city_id)
    return ApiEnvelope(data=result)


@router.get(
    "/cities/{city_id}/alerts",
    response_model=ApiEnvelope[list[AqiAlertOut]],
)
async def list_alerts(
    city_id: str,
    active_only: bool = Query(False, description="Return only currently active alerts"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Return alert history for a city, ordered most-recent first."""
    alerts = await repo.list_alerts(db, city_id, active_only=active_only, limit=limit)
    return ApiEnvelope(data=[AqiAlertOut.model_validate(a) for a in alerts])
