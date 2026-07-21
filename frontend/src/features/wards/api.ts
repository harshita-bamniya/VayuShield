import client from "@/lib/apiClient";
import type { ApiEnvelope, WardDetail, WardWithAqi } from "@/lib/types";
import type { ForecastRun } from "@/features/forecast/api";

export async function fetchWardsWithAqi(cityId: string): Promise<WardWithAqi[]> {
  const resp = await client.get<ApiEnvelope<WardWithAqi[]>>(`/cities/${cityId}/wards?limit=500`);
  return resp.data.data ?? [];
}

export async function fetchWardDetail(cityId: string, wardId: string): Promise<WardDetail> {
  const resp = await client.get<ApiEnvelope<WardDetail>>(
    `/cities/${cityId}/wards/${wardId}`
  );
  return resp.data.data!;
}

export async function fetchWardForecast(cityId: string, wardId: string): Promise<ForecastRun> {
  const resp = await client.get<ApiEnvelope<ForecastRun>>(
    `/cities/${cityId}/wards/${wardId}/forecast`
  );
  return resp.data.data!;
}
