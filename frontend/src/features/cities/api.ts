import client from "@/lib/apiClient";
import type { City, Ward } from "@/lib/types";

export interface StationOut {
  id: string;
  city_id: string;
  ward_id: string | null;
  external_station_code: string;
  name: string;
  geometry: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface CityWithCounts extends City {
  config_json: Record<string, unknown>;
  created_at: string;
}

export async function fetchCities(): Promise<CityWithCounts[]> {
  const resp = await client.get<{ data: CityWithCounts[] }>("/cities");
  return resp.data.data ?? [];
}

export async function fetchCity(cityId: string): Promise<CityWithCounts> {
  const resp = await client.get<{ data: CityWithCounts }>(`/cities/${cityId}`);
  return resp.data.data!;
}

export async function fetchWards(cityId: string): Promise<Ward[]> {
  const resp = await client.get<{ data: Ward[] }>(`/cities/${cityId}/wards`);
  return resp.data.data ?? [];
}

export async function fetchStations(cityId: string): Promise<StationOut[]> {
  const resp = await client.get<{ data: StationOut[] }>(`/cities/${cityId}/stations`);
  return resp.data.data ?? [];
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export interface CreateCityPayload {
  name: string;
  state: string;
  timezone: string;
  config_json?: Record<string, unknown>;
}

export async function createCity(payload: CreateCityPayload): Promise<CityWithCounts> {
  const resp = await client.post<{ data: CityWithCounts }>("/cities", payload);
  return resp.data.data!;
}

export interface CreateWardPayload {
  name: string;
  population?: number | null;
  geometry?: Record<string, unknown> | null;
}

export async function createWard(cityId: string, payload: CreateWardPayload): Promise<Ward> {
  const resp = await client.post<{ data: Ward }>(`/cities/${cityId}/wards`, payload);
  return resp.data.data!;
}

export interface CreateStationPayload {
  name: string;
  external_station_code: string;
  geometry?: Record<string, unknown> | null;
  ward_id?: string | null;
  is_active?: boolean;
}

export async function createStation(cityId: string, payload: CreateStationPayload): Promise<StationOut> {
  const resp = await client.post<{ data: StationOut }>(`/cities/${cityId}/stations`, payload);
  return resp.data.data!;
}
