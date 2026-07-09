import client from "@/lib/apiClient";

export interface ReportCity {
  id: string;
  name: string;
  state: string;
  timezone: string;
}

export interface AqiStats {
  current_avg_aqi: number | null;
  peak_aqi_7d: number | null;
  category_breakdown: Record<string, number>;
}

export interface EnforcementBrief {
  id: string;
  source_name: string;
  source_type: string;
  priority_score: number;
  status: string;
}

export interface ForecastSummary {
  next_24h_peak_aqi: number | null;
  dominant_hour: number | null;
}

export interface AttributionSummary {
  dominant_source: string | null;
  breakdown: Record<string, number>;
}

export interface WardAqiRow {
  ward_id: string;
  ward_name: string;
  avg_aqi: number | null;
  reading_count: number;
}

export interface ReportSummary {
  city: ReportCity;
  period_days: number;
  aqi_stats: AqiStats;
  top_enforcement_items: EnforcementBrief[];
  advisory_count_by_language: Record<string, number>;
  forecast: ForecastSummary;
  attribution: AttributionSummary;
  ward_aqi_table: WardAqiRow[];
}

export async function fetchReportSummary(cityId: string, days: number): Promise<ReportSummary> {
  const resp = await client.get<{ data: ReportSummary }>(
    `/cities/${cityId}/reports/summary`,
    { params: { days } }
  );
  return resp.data.data;
}

export function buildCsvUrl(cityId: string, days: number): string {
  const token = localStorage.getItem("access_token") ?? "";
  // The CSV endpoint returns a file download — we build the URL and open it directly.
  // Token is passed as query param since browser download doesn't send auth headers.
  const base = "/api/v1";
  return `${base}/cities/${cityId}/reports/summary.csv?days=${days}&token=${token}`;
}
