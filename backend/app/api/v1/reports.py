"""Reports & Export API — Module 12."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.middleware import require_city_scope
from app.core.security import require_role
from app.modules.reports import service
from app.modules.reports.schemas import ReportSummaryOut
from app.schemas.common import ApiEnvelope

router = APIRouter(tags=["reports"])


@router.get(
    "/cities/{city_id}/reports/summary",
    response_model=ApiEnvelope[ReportSummaryOut],
)
async def get_report_summary(
    city_id: str,
    days: int = Query(7, ge=1, le=90, description="Look-back period in days (1–90)"),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
    _role: dict = Depends(require_role("admin", "sysadmin")),
):
    """Return a full city air-quality summary for the given look-back period."""
    summary = await service.build_summary(db, city_id, days)
    if not summary:
        raise NotFoundError(f"City {city_id} not found")
    return ApiEnvelope(data=summary)


@router.get("/cities/{city_id}/reports/summary.csv")
async def get_report_summary_csv(
    city_id: str,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _caller: dict = Depends(require_city_scope),
    _role: dict = Depends(require_role("admin", "sysadmin")),
):
    """Same data as the JSON summary, flattened to CSV (one row per stat key)."""
    summary = await service.build_summary(db, city_id, days)
    if not summary:
        raise NotFoundError(f"City {city_id} not found")
    csv_text = service.summary_to_csv(summary)
    filename = f"vayushield_report_{city_id[:8]}_{days}d.csv"
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
