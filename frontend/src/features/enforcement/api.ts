import client from "@/lib/apiClient";

export interface EnforcementSource {
  id: string;
  name: string;
  type: string;
  permit_status: string;
  last_inspected_at: string | null;
}

export interface EnforcementItem {
  id: string;
  city_id: string;
  emission_source_id: string;
  priority_score: number;
  evidence_brief_text: string | null;
  status: string;
  attribution_id: string | null;
  forecast_id: string | null;
  created_at: string;
  updated_at: string;
  source: EnforcementSource | null;
}

export interface EnforcementListOut {
  items: EnforcementItem[];
  total: number;
}

export interface InspectionOut {
  id: string;
  enforcement_queue_id: string;
  inspector_id: string | null;
  scheduled_at: string | null;
  completed_at: string | null;
  outcome: string | null;
  notes: string | null;
  created_at: string;
}

export async function fetchEnforcementQueue(
  cityId: string,
  status?: string,
): Promise<EnforcementListOut> {
  const params = status ? { status } : {};
  const resp = await client.get<{ data: EnforcementListOut }>(
    `/cities/${cityId}/enforcement`,
    { params },
  );
  return resp.data.data;
}

export async function rankEnforcementQueue(cityId: string): Promise<EnforcementListOut> {
  const resp = await client.post<{ data: EnforcementListOut }>(
    `/cities/${cityId}/enforcement/rank`,
  );
  return resp.data.data;
}

export async function updateEnforcementStatus(
  cityId: string,
  itemId: string,
  status: string,
): Promise<void> {
  await client.patch(`/cities/${cityId}/enforcement/${itemId}`, { status });
}

export async function logInspection(
  cityId: string,
  itemId: string,
  payload: { outcome: string; notes?: string; completed_at?: string },
): Promise<InspectionOut> {
  const resp = await client.post<{ data: InspectionOut }>(
    `/cities/${cityId}/enforcement/${itemId}/inspections`,
    payload,
  );
  return resp.data.data;
}

export async function fetchPendingCount(cityId: string): Promise<number> {
  const resp = await client.get<{ data: { pending: number } }>(
    `/cities/${cityId}/enforcement-count`,
  );
  return resp.data.data.pending;
}
