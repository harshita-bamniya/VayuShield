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
  cityId: string;
  name: string;
  population: number;
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
  forecastForTs: string;
  predictedAqi: number;
  predictedPm25: number;
  modelVersion: string;
}

export type EnforcementStatus = "pending" | "dispatched" | "completed";

export interface EnforcementItem {
  id: string;
  emissionSourceId: string;
  priorityScore: number;
  evidenceBriefText: string;
  status: EnforcementStatus;
}

export type AdvisoryChannel = "web" | "sms" | "push";

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
