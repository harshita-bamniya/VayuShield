import client from "@/lib/apiClient";

export interface ForecastPoint {
  id: string;
  city_id: string;
  generated_at: string;
  forecast_for_ts: string;
  predicted_aqi: number;
  predicted_pm25: number | null;
  confidence: number | null;
  model_version: string;
  is_stale: boolean;
}

export interface ForecastRun {
  city_id: string;
  generated_at: string;
  model_version: string;
  horizon_hours: number;
  points: ForecastPoint[];
  peak_aqi: number;
  peak_at: string;
  is_stale: boolean;
}

export async function fetchForecast(cityId: string, recompute = false): Promise<ForecastRun> {
  const qs = recompute ? "?recompute=true" : "";
  const resp = await client.get<{ data: ForecastRun }>(`/cities/${cityId}/forecast${qs}`);
  return resp.data.data!;
}

export async function runForecast(cityId: string): Promise<ForecastRun> {
  const resp = await client.post<{ data: ForecastRun }>(`/cities/${cityId}/forecast/run`);
  return resp.data.data!;
}
