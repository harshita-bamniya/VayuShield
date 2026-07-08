import client from "@/lib/apiClient";
import type { Advisory } from "@/lib/types";

export interface AdvisoryListOut {
  items: Advisory[];
  total: number;
}

export interface AdvisoryGenerateResponse {
  generated: number;
  skipped: number;
  advisories: Advisory[];
}

export async function fetchAdvisories(
  cityId: string,
  params?: { language?: string; channel?: string; limit?: number; offset?: number }
): Promise<AdvisoryListOut> {
  const resp = await client.get<{ data: AdvisoryListOut }>(
    `/cities/${cityId}/advisories`,
    { params }
  );
  return resp.data.data;
}

export async function fetchAdvisory(cityId: string, advisoryId: string): Promise<Advisory> {
  const resp = await client.get<{ data: Advisory }>(
    `/cities/${cityId}/advisories/${advisoryId}`
  );
  return resp.data.data;
}

export async function generateAdvisories(cityId: string): Promise<AdvisoryGenerateResponse> {
  const resp = await client.post<{ data: AdvisoryGenerateResponse }>(
    `/cities/${cityId}/advisories/generate`
  );
  return resp.data.data;
}

export async function fetchAdvisoryCount(cityId: string): Promise<number> {
  const resp = await client.get<{ data: { city_id: string; total: number } }>(
    `/cities/${cityId}/advisory-count`
  );
  return resp.data.data.total;
}
