"""Forecasting API — Module 05."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.middleware import require_city_scope
from app.modules.forecasting import service, ward_service
from app.modules.forecasting.schemas import ForecastRunOut
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["forecasting"])


@router.get(
    "/cities/{city_id}/forecast",
    response_model=ApiEnvelope[ForecastRunOut],
)
async def get_forecast(
    city_id: str,
    recompute: bool = Query(False, description="Force a fresh forecast run before returning"),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Return the 72-hour AQI forecast for a city.

    Serves the cached latest run by default. Pass `?recompute=true` to force a fresh run.
    """
    if recompute:
        result = await service.run_forecast(db, city_id)
        return ApiEnvelope(data=result)

    result = await service.get_latest_forecast(db, city_id)
    if result is None:
        result = await service.run_forecast(db, city_id)
    return ApiEnvelope(data=result)


@router.post(
    "/cities/{city_id}/forecast/run",
    response_model=ApiEnvelope[ForecastRunOut],
)
async def run_forecast(
    city_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Trigger a fresh 72-hour forecast computation and persist results."""
    result = await service.run_forecast(db, city_id)
    return ApiEnvelope(data=result)


@router.get(
    "/cities/{city_id}/wards/{ward_id}/forecast",
    response_model=ApiEnvelope[ForecastRunOut],
)
async def get_ward_forecast(
    city_id: str,
    ward_id: str,
    recompute: bool = Query(False, description="Force a fresh ward forecast run"),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Return the 72-hour hyperlocal AQI forecast for a specific ward.

    Uses Open-Meteo forward wind/temp and emission-source proximity to produce
    a ward-specific prediction that differs from the city average.
    Pass `?recompute=true` to force a fresh run.
    """
    if recompute:
        result = await ward_service.run_ward_forecast(db, city_id, ward_id)
        return ApiEnvelope(data=result)

    result = await ward_service.get_latest_ward_forecast(db, city_id, ward_id)
    if result is None:
        result = await ward_service.run_ward_forecast(db, city_id, ward_id)
    return ApiEnvelope(data=result)


@router.post(
    "/cities/{city_id}/wards/{ward_id}/forecast/run",
    response_model=ApiEnvelope[ForecastRunOut],
)
async def run_ward_forecast(
    city_id: str,
    ward_id: str,
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
):
    """Trigger a fresh hyperlocal ward forecast and persist results."""
    result = await ward_service.run_ward_forecast(db, city_id, ward_id)
    return ApiEnvelope(data=result)
