// Canonical shared types — ALL frontend modules import from here, never redeclare
// Owned by Module 00 skeleton; extended by each module as needed. Do NOT fork.

export type Role = "admin" | "inspector" | "sysadmin";

export interface UserOut {
  id: string;
  email: string;
  role: Role;
  city_id: string | null;
  full_name: string | null;
  is_active: boolean;
}

export interface City {
  id: string;
  name: string;
  state: string;
  timezone: string;
}

export interface Ward {
  id: string;
  city_id: string;
  name: string;
  population: number;
}

export interface StationReadingBrief {
  station_id: string | null;
  station_name: string | null;
  external_station_code: string | null;
  ts: string | null;
  pm25: number | null;
  pm10: number | null;
  aqi: number | null;
  aqi_category: string | null;
  is_stale: boolean | null;
}

export interface WardWithAqi {
  id: string;
  city_id: string;
  name: string;
  geometry: Record<string, unknown> | null;
  population: number | null;
  vulnerable_site_flags: Record<string, unknown>;
  created_at: string;
  avg_aqi: number | null;
  aqi_category: string | null;
}

export interface WardDetail extends WardWithAqi {
  station_readings: StationReadingBrief[];
  attribution_breakdown: Record<string, number>;
  dominant_source: string | null;
  advisory_count: number;
}

export type SourceCategory = "vehicular" | "industrial" | "construction" | "agricultural";

export interface Attribution {
  wardId: string;
  ts: string;
  dominantSource: SourceCategory;
  confidenceScore: number; // 0–100
  isStale: boolean;
}

export interface ForecastPoint {
  forecast_for_ts: string;
  predicted_aqi: number;
  predicted_pm25: number | null;
  model_version: string;
}

export type EnforcementStatus = "pending" | "dispatched" | "completed";

export interface EnforcementItem {
  id: string;
  emissionSourceId: string;
  priorityScore: number;
  evidenceBriefText: string;
  status: EnforcementStatus;
}

export type AdvisoryChannel = "web" | "sms" | "push" | "whatsapp";

export interface Advisory {
  id: string;
  city_id: string;
  ward_id: string | null;
  language: string;
  title: string;
  body: string;
  aqi_level: string;
  dominant_source: string | null;
  channel: AdvisoryChannel;
  sent_at: string | null;
  created_at: string;
}

export interface ApiEnvelope<T> {
  data: T | null;
  meta: { page: number; limit: number; total: number } | null;
  error: { code: string; message: string; details?: Record<string, string> } | null;
}
