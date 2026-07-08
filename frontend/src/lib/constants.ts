export const AQI_BANDS = [
  { label: "Good", min: 0, max: 50, color: "#00B050", pattern: "circle" },
  { label: "Satisfactory", min: 51, max: 100, color: "#92D050", pattern: "square" },
  { label: "Moderate", min: 101, max: 200, color: "#FFFF00", pattern: "triangle" },
  { label: "Poor", min: 201, max: 300, color: "#FF0000", pattern: "diamond" },
  { label: "Very Poor", min: 301, max: 400, color: "#C00000", pattern: "cross" },
  { label: "Severe", min: 401, max: 500, color: "#7030A0", pattern: "star" },
] as const;

export const SUPPORTED_LANGUAGES = ["hi", "mr", "kn", "ta", "bn", "gu"] as const;

export const SOURCE_CATEGORIES = [
  "vehicular",
  "industrial",
  "construction",
  "agricultural",
] as const;

export const STALENESS_THRESHOLD_HOURS = 2;
export const ADVISORY_LEAD_TIME_HOURS = 18;
export const FORECAST_HORIZON_HOURS = 72;
export const GRID_RESOLUTION_KM = 1;

export const API_BASE = "/api/v1";
