"""Reports — service layer."""

import csv
import io

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports import repository as repo
from app.modules.reports.schemas import (
    AqiStats,
    AttributionSummary,
    CityInfo,
    EnforcementBrief,
    EnforcementStats,
    ForecastSummary,
    ReportSummaryOut,
    WardAqiRow,
)


async def build_summary(db: AsyncSession, city_id: str, days: int) -> ReportSummaryOut | None:
    city_row = await repo.get_city_info(db, city_id)
    if not city_row:
        return None

    aqi_raw, enf_rows, adv_counts, fc_raw, attr_raw, ward_rows, enf_stats = await _gather(
        db, city_id, days
    )

    city = CityInfo(**city_row)
    aqi_stats = AqiStats(
        current_avg_aqi=aqi_raw["current_avg_aqi"],
        peak_aqi_7d=aqi_raw["peak_aqi_7d"],
        category_breakdown=aqi_raw["category_breakdown"],
    )
    top_items = [
        EnforcementBrief(
            id=r["id"],
            source_name=r["source_name"],
            source_type=r["source_type"],
            priority_score=r["priority_score"],
            status=r["status"],
        )
        for r in enf_rows
    ]
    forecast = ForecastSummary(**fc_raw)
    attribution = AttributionSummary(**attr_raw)
    wards = [WardAqiRow(**w) for w in ward_rows]

    return ReportSummaryOut(
        city=city,
        period_days=days,
        aqi_stats=aqi_stats,
        top_enforcement_items=top_items,
        advisory_count_by_language=adv_counts,
        forecast=forecast,
        attribution=attribution,
        ward_aqi_table=wards,
        enforcement_stats=EnforcementStats(**enf_stats),
    )


async def _gather(db: AsyncSession, city_id: str, days: int):
    aqi_raw = await repo.get_aqi_stats(db, city_id, days)
    enf_rows = await repo.get_top_enforcement_items(db, city_id, limit=3)
    adv_counts = await repo.get_advisory_count_by_language(db, city_id)
    fc_raw = await repo.get_forecast_summary(db, city_id)
    attr_raw = await repo.get_attribution_summary(db, city_id)
    ward_rows = await repo.get_ward_aqi_table(db, city_id, days)
    enf_stats = await repo.get_enforcement_stats(db, city_id, days)
    return aqi_raw, enf_rows, adv_counts, fc_raw, attr_raw, ward_rows, enf_stats


def summary_to_csv(summary: ReportSummaryOut) -> str:
    """Flatten the summary to CSV rows: stat_key, value."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["stat_key", "value"])

    writer.writerow(["city_name", summary.city.name])
    writer.writerow(["city_state", summary.city.state])
    writer.writerow(["city_timezone", summary.city.timezone])
    writer.writerow(["period_days", summary.period_days])
    writer.writerow(["current_avg_aqi", summary.aqi_stats.current_avg_aqi])
    writer.writerow(["peak_aqi_7d", summary.aqi_stats.peak_aqi_7d])

    for cat, pct in summary.aqi_stats.category_breakdown.items():
        writer.writerow([f"aqi_category_pct_{cat.lower().replace(' ', '_')}", pct])

    for i, item in enumerate(summary.top_enforcement_items, start=1):
        writer.writerow([f"enforcement_top{i}_source", item.source_name])
        writer.writerow([f"enforcement_top{i}_score", item.priority_score])
        writer.writerow([f"enforcement_top{i}_status", item.status])

    for lang, cnt in summary.advisory_count_by_language.items():
        writer.writerow([f"advisory_count_{lang}", cnt])

    writer.writerow(["forecast_next24h_peak_aqi", summary.forecast.next_24h_peak_aqi])
    writer.writerow(["forecast_dominant_hour_utc", summary.forecast.dominant_hour])
    writer.writerow(["attribution_dominant_source", summary.attribution.dominant_source])

    for src, pct in summary.attribution.breakdown.items():
        writer.writerow([f"attribution_pct_{src}", pct])

    # Ward AQI table — separate section
    writer.writerow([])
    writer.writerow(["ward_id", "ward_name", "avg_aqi", "reading_count"])
    for w in summary.ward_aqi_table:
        writer.writerow([w.ward_id, w.ward_name, w.avg_aqi, w.reading_count])

    return output.getvalue()
