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

// ── Fire Hotspots ─────────────────────────────────────────────────────────────

export interface FireHotspot {
  id: string;
  detected_at: string;
  lat: number;
  lon: number;
  confidence: number;
  frp: number | null;
  source: string;
}

export async function fetchFireHotspots(cityId: string, hoursBack = 24): Promise<FireHotspot[]> {
  const resp = await client.get<{ data: FireHotspot[] }>(
    `/cities/${cityId}/fire-hotspots?hours_back=${hoursBack}`
  );
  return resp.data.data ?? [];
}

// ── Traffic Snapshots ─────────────────────────────────────────────────────────

export interface TrafficSegment {
  segment_id: string;
  segment_name: string | null;
  congestion_ratio: number;
  current_speed: number | null;
  free_flow_speed: number | null;
  lat: number | null;
  lon: number | null;
  ts: string;
  is_mock: boolean;
}

export async function fetchTrafficSegments(cityId: string): Promise<TrafficSegment[]> {
  const resp = await client.get<{ data: TrafficSegment[] }>(`/cities/${cityId}/traffic`);
  return resp.data.data ?? [];
}

// ── Satellite Observations ────────────────────────────────────────────────────

export interface SatelliteObs {
  observed_date: string;
  aod_value: number | null;
  estimated_pm25: number | null;
  source: string;
  is_mock: boolean;
}

export async function fetchSatelliteObs(cityId: string): Promise<SatelliteObs[]> {
  const resp = await client.get<{ data: SatelliteObs[] }>(`/cities/${cityId}/satellite`);
  return resp.data.data ?? [];
}

export async function pollSatelliteAod(cityId: string): Promise<SatelliteObs> {
  const resp = await client.post<{ data: SatelliteObs }>(`/cities/${cityId}/satellite/poll`);
  return resp.data.data!;
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

export interface UpdateStationPayload {
  ward_id?: string | null;
  name?: string;
  is_active?: boolean;
}

export async function updateStation(
  cityId: string,
  stationId: string,
  payload: UpdateStationPayload
): Promise<StationOut> {
  const resp = await client.patch<{ data: StationOut }>(
    `/cities/${cityId}/stations/${stationId}`,
    payload
  );
  return resp.data.data!;
}

export async function deleteCity(cityId: string): Promise<void> {
  await client.delete(`/cities/${cityId}`);
}

export async function deleteWard(cityId: string, wardId: string): Promise<void> {
  await client.delete(`/cities/${cityId}/wards/${wardId}`);
}

export async function deleteStation(cityId: string, stationId: string): Promise<void> {
  await client.delete(`/cities/${cityId}/stations/${stationId}`);
}

export interface DiscoverSourcesResult {
  discovered: number;
  imported: number;
  skipped: number;
  error?: string | null;
}

export async function discoverEmissionSources(cityId: string): Promise<DiscoverSourcesResult> {
  const resp = await client.post<{ data: DiscoverSourcesResult }>(
    `/cities/${cityId}/emission-sources/discover`
  );
  return resp.data.data!;
}

export async function initializeCityData(cityId: string): Promise<{ readings: number }> {
  // 1. Poll real CPCB station data + weather in parallel
  const [readingsResp] = await Promise.all([
    client.post<{ data: { inserted: number } }>(`/cities/${cityId}/readings/poll`),
    client.post(`/cities/${cityId}/weather/poll`),
  ]);
  // 2. Run forecast from fresh readings
  await client.post(`/cities/${cityId}/forecast/run`);
  // 3. Re-rank enforcement queue
  await client.post(`/cities/${cityId}/enforcement/rank`);
  return { readings: readingsResp.data.data?.inserted ?? 0 };
}
