import client from "@/lib/apiClient";
import type { ApiEnvelope, WardDetail, WardWithAqi } from "@/lib/types";

export async function fetchWardsWithAqi(cityId: string): Promise<WardWithAqi[]> {
  const resp = await client.get<ApiEnvelope<WardWithAqi[]>>(`/cities/${cityId}/wards`);
  return resp.data.data ?? [];
}

export async function fetchWardDetail(cityId: string, wardId: string): Promise<WardDetail> {
  const resp = await client.get<ApiEnvelope<WardDetail>>(
    `/cities/${cityId}/wards/${wardId}`
  );
  return resp.data.data!;
}
