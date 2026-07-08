import client from "@/lib/apiClient";
import type { City, Ward } from "@/lib/types";

export interface StationOut {
  id: string;
  cityId: string;
  wardId: string | null;
  externalStationCode: string;
  name: string;
  geometry: Record<string, unknown> | null;
  isActive: boolean;
  createdAt: string;
}

export async function fetchCities(): Promise<City[]> {
  const resp = await client.get<{ data: City[] }>("/cities");
  return resp.data.data ?? [];
}

export async function fetchCity(cityId: string): Promise<City> {
  const resp = await client.get<{ data: City }>(`/cities/${cityId}`);
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
