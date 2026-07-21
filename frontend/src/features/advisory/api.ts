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

export interface IvrAdvisory {
  ivr_text: string;
  language: string;
  aqi_level?: string;
  advisory_id?: string;
}

export async function fetchIvrAdvisory(
  cityId: string,
  language: string = "en",
  wardId?: string
): Promise<IvrAdvisory> {
  const resp = await client.get<{ data: IvrAdvisory }>(
    `/cities/${cityId}/advisories/ivr`,
    { params: { language, ...(wardId ? { ward_id: wardId } : {}) } }
  );
  return resp.data.data;
}

export interface WhatsAppDeliveryResult {
  status: "sent" | "mock" | "error";
  channel: "whatsapp";
  phone: string;
  sent_at: string;
  mock: boolean;
  sid: string | null;
  error: string | null;
}

export async function sendAdvisoryWhatsApp(
  cityId: string,
  advisoryId: string,
  phone?: string
): Promise<WhatsAppDeliveryResult> {
  const resp = await client.post<{ data: WhatsAppDeliveryResult }>(
    `/cities/${cityId}/advisories/${advisoryId}/send`,
    null,
    { params: phone ? { phone } : undefined }
  );
  return resp.data.data;
}

export async function generateWardAdvisories(
  cityId: string,
  wardId: string
): Promise<AdvisoryGenerateResponse> {
  const resp = await client.post<{ data: AdvisoryGenerateResponse }>(
    `/cities/${cityId}/wards/${wardId}/advisories/generate`
  );
  return resp.data.data;
}
