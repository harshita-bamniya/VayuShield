import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import { fetchCities, fetchCity, fetchFireHotspots, fetchSatelliteObs, fetchTrafficSegments, type CityWithCounts } from "@/features/cities/api";
import { fetchForecast } from "@/features/forecast/api";
import ForecastChart from "@/features/forecast/ForecastChart";
import { fetchPendingCount } from "@/features/enforcement/api";
import { fetchAdvisoryCount } from "@/features/advisory/api";
import { fetchWardsWithAqi } from "@/features/wards/api";
import WardMap from "@/components/WardMap";
import client from "@/lib/apiClient";

interface AqiAlert {
  id: string;
  alert_level: string;
  aqi_value: number;
  dominant_source: string | null;
  triggered_at: string;
  resolved_at: string | null;
  is_active: boolean;
}

async function fetchAlerts(cityId: string): Promise<AqiAlert[]> {
  const resp = await client.get<{ data: AqiAlert[] }>(`/cities/${cityId}/alerts?limit=5`);
  return resp.data.data ?? [];
}

interface AttributionResult {
  dominant_source: string | null;
  ranked_sources: { source_type: string; contribution_pct: number; rank: number }[];
  confidence_score: number | null;
  pollutant_snapshot: { pm25: number | null; pm10: number | null; no2: number | null; so2: number | null; co: number | null; o3: number | null } | null;
  wind_description: string | null;
  aqi: number | null;
}

async function fetchAttribution(cityId: string): Promise<AttributionResult> {
  const resp = await client.get<{ data: AttributionResult }>(`/cities/${cityId}/attribution?recompute=true`);
  return resp.data.data!;
}


function aqiCategory(aqi: number): string {
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

function aqiColor(aqi: number): string {
  if (aqi <= 50) return "text-green-400";
  if (aqi <= 100) return "text-lime-400";
  if (aqi <= 200) return "text-yellow-400";
  if (aqi <= 300) return "text-orange-400";
  if (aqi <= 400) return "text-red-400";
  return "text-purple-400";
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { selectedCityId, selectedCity, setSelectedCity } = useCities();

  const isSysadmin = user?.role === "sysadmin";

  const { data: cities } = useQuery({
    queryKey: ["cities"],
    queryFn: fetchCities,
    enabled: isSysadmin,
  });

  const { data: userCity } = useQuery({
    queryKey: ["city", user?.city_id],
    queryFn: () => fetchCity(user!.city_id!),
    enabled: !isSysadmin && !!user?.city_id,
  });

  useEffect(() => {
    if (!selectedCityId) {
      if (userCity) setSelectedCity(userCity);
      else if (cities && cities.length > 0) setSelectedCity(cities[0]);
    }
  }, [cities, userCity, selectedCityId, setSelectedCity]);

  // Forecast query — runs once city is selected
  const { data: forecast, isLoading: forecastLoading } = useQuery({
    queryKey: ["forecast", selectedCityId],
    queryFn: () => fetchForecast(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 15, // treat fresh for 15 min
  });

  const { data: pendingCount } = useQuery({
    queryKey: ["enforcement-count", selectedCityId],
    queryFn: () => fetchPendingCount(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const { data: advisoryCount } = useQuery({
    queryKey: ["advisory-count", selectedCityId],
    queryFn: () => fetchAdvisoryCount(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const { data: wards = [] } = useQuery({
    queryKey: ["wards-aqi", selectedCityId],
    queryFn: () => fetchWardsWithAqi(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const { data: fireHotspots = [] } = useQuery({
    queryKey: ["fire-hotspots", selectedCityId],
    queryFn: () => fetchFireHotspots(selectedCityId!),
    enabled: !!selectedCityId,
    refetchInterval: 1000 * 60 * 5,
    staleTime: 1000 * 60 * 5,
  });

  const { data: attribution } = useQuery({
    queryKey: ["attribution", selectedCityId],
    queryFn: () => fetchAttribution(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 10,
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["alerts", selectedCityId],
    queryFn: () => fetchAlerts(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 2,
  });

  const [showSatellite, setShowSatellite] = useState(false);
  const [showTraffic, setShowTraffic] = useState(false);

  const { data: trafficSegments = [] } = useQuery({
    queryKey: ["traffic", selectedCityId],
    queryFn: () => fetchTrafficSegments(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  });

  const { data: satelliteObs = [] } = useQuery({
    queryKey: ["satellite-obs", selectedCityId],
    queryFn: () => fetchSatelliteObs(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 60, // 1h — daily data
  });

  const displayCity = selectedCity;
  const currentAqi = attribution?.aqi ?? forecast?.points[0]?.predicted_aqi;
  const latestSat = satelliteObs[0] ?? null;

  const avgCongestion = trafficSegments.length > 0
    ? trafficSegments.reduce((s, t) => s + t.congestion_ratio, 0) / trafficSegments.length
    : null;
  const heavySegments = trafficSegments.filter((t) => t.congestion_ratio >= 2.5).length;

  // Map center: read from city config_json lat/lon, fall back to Delhi
  const mapCenter: [number, number] = (() => {
    const cfg = (selectedCity as CityWithCounts | undefined)?.config_json as Record<string, unknown> | undefined;
    const lat = typeof cfg?.lat === "number" ? cfg.lat : null;
    const lon = typeof cfg?.lon === "number" ? cfg.lon : null;
    return lat && lon ? [lat, lon] : [28.62, 77.21];
  })();

  const statCards = [
    {
      label: "City AQI (Max)",
      value: currentAqi != null ? String(currentAqi) : "—",
      desc: currentAqi != null ? aqiCategory(currentAqi) : "Loading…",
      color: currentAqi != null ? aqiColor(currentAqi) : "text-slate-400",
    },
    {
      label: "Peak Forecast AQI",
      value: forecast?.peak_aqi != null ? String(forecast.peak_aqi) : "—",
      desc: "Next 72 hours",
      color: forecast?.peak_aqi != null ? aqiColor(forecast.peak_aqi) : "text-slate-400",
    },
    {
      label: "Pending Inspections",
      value: pendingCount != null ? String(pendingCount) : "—",
      desc: "In queue",
      color: "text-orange-400",
    },
    {
      label: "Advisories Sent",
      value: advisoryCount != null ? String(advisoryCount) : "—",
      desc: "Total issued",
      color: "text-green-400",
    },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-950 text-white">
        {/* Topbar */}
        <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-white">Dashboard</h1>
            {displayCity && (
              <span className="px-2 py-0.5 rounded-md text-xs bg-slate-800 text-slate-400 border border-slate-700">
                {displayCity.name}, {displayCity.state}
              </span>
            )}
          </div>
          {isSysadmin && cities && cities.length > 1 && (
            <select
              className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={selectedCityId ?? ""}
              onChange={(e) => {
                const city = cities.find((c) => c.id === e.target.value);
                if (city) setSelectedCity(city);
              }}
            >
              {cities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live data
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {statCards.map((card) => (
              <div
                key={card.label}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5"
              >
                <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">
                  {card.label}
                </p>
                <p className={`text-3xl font-bold ${card.color} mb-1`}>{card.value}</p>
                <p className="text-xs text-slate-500">
                  {displayCity ? `${displayCity.name} · ` : ""}
                  {card.desc}
                </p>
              </div>
            ))}
          </div>

          {/* Pollutant Readings + Source Attribution */}
          {attribution && (
            <div className="grid lg:grid-cols-2 gap-4 mb-4">
              {/* Pollutant snapshot */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-200">Live Pollutant Readings</p>
                    <p className="text-xs text-slate-500 mt-0.5">Latest station averages · µg/m³ unless noted</p>
                  </div>
                  {attribution.wind_description && (
                    <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
                      🌬 {attribution.wind_description}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { key: "pm25", label: "PM2.5", unit: "µg/m³", thresholds: [60, 90, 120], signal: "Combustion / burning" },
                    { key: "pm10", label: "PM10", unit: "µg/m³", thresholds: [100, 150, 200], signal: "Coarse dust / construction" },
                    { key: "no2",  label: "NO₂",  unit: "µg/m³", thresholds: [40, 80, 120],  signal: "Vehicular / industrial" },
                    { key: "so2",  label: "SO₂",  unit: "µg/m³", thresholds: [8, 20, 40],    signal: "Industrial / coal burning" },
                    { key: "co",   label: "CO",   unit: "mg/m³", thresholds: [0.8, 2.0, 3.5], signal: "Vehicles / incomplete combustion" },
                    { key: "o3",   label: "O₃",   unit: "µg/m³", thresholds: [50, 80, 120],  signal: "Photochemical smog" },
                  ].map(({ key, label, unit, thresholds, signal }) => {
                    const val = attribution.pollutant_snapshot?.[key as keyof typeof attribution.pollutant_snapshot];
                    const numVal = typeof val === "number" ? val : null;
                    const color = numVal == null ? "text-slate-600"
                      : numVal > thresholds[2] ? "text-red-400"
                      : numVal > thresholds[1] ? "text-orange-400"
                      : numVal > thresholds[0] ? "text-yellow-400"
                      : "text-green-400";
                    return (
                      <div key={key} className="bg-slate-800 rounded-lg p-3" title={signal}>
                        <p className="text-xs text-slate-500 mb-1">{label}</p>
                        <p className={`text-xl font-bold font-mono ${color}`}>
                          {numVal != null ? numVal.toFixed(key === "co" ? 2 : 1) : "—"}
                        </p>
                        <p className="text-xs text-slate-600 mt-0.5">{unit}</p>
                      </div>
                    );
                  })}
                </div>
                {attribution.pollutant_snapshot?.pm25 && attribution.pollutant_snapshot?.pm10 && (
                  <div className="mt-3 text-xs text-slate-500">
                    PM10/PM2.5 ratio: <span className="font-mono text-slate-300">
                      {(attribution.pollutant_snapshot.pm10 / attribution.pollutant_snapshot.pm25).toFixed(2)}
                    </span>
                    <span className="ml-2 text-slate-600">
                      {(attribution.pollutant_snapshot.pm10 / attribution.pollutant_snapshot.pm25) > 2.5
                        ? "→ coarse dust (construction / road)" : "→ fine particles (combustion)"}
                    </span>
                  </div>
                )}
              </div>

              {/* Attribution breakdown */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-200">Source Attribution</p>
                    <p className="text-xs text-slate-500 mt-0.5">Chemical fingerprint + wind dispersion hybrid</p>
                  </div>
                  {attribution.confidence_score != null && (
                    <span className={`text-xs px-2 py-1 rounded font-semibold ${
                      attribution.confidence_score >= 0.75 ? "bg-green-500/20 text-green-400"
                      : attribution.confidence_score >= 0.5 ? "bg-yellow-500/20 text-yellow-400"
                      : "bg-slate-700 text-slate-400"
                    }`}>
                      {Math.round(attribution.confidence_score * 100)}% confidence
                    </span>
                  )}
                </div>
                <div className="space-y-2.5">
                  {(() => {
                    const SOURCE_COLORS: Record<string, string> = {
                      vehicular: "#f97316", industrial: "#8b5cf6",
                      construction: "#eab308", agricultural: "#22c55e",
                      fire: "#ef4444", other: "#64748b",
                    };
                    const SOURCE_ICONS: Record<string, string> = {
                      vehicular: "🚗", industrial: "🏭",
                      construction: "🏗️", agricultural: "🌾",
                      fire: "🔥", other: "💨",
                    };
                    return (attribution.ranked_sources ?? [])
                      .filter(s => s.contribution_pct > 0.1)
                      .map(src => (
                        <div key={src.source_type}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-slate-300 capitalize flex items-center gap-1.5">
                              {SOURCE_ICONS[src.source_type] ?? "💨"} {src.source_type}
                              {src.rank === 1 && (
                                <span className="text-xs bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded font-semibold">Dominant</span>
                              )}
                            </span>
                            <span className="text-xs font-mono text-slate-300">{src.contribution_pct.toFixed(1)}%</span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-2">
                            <div
                              className="h-2 rounded-full transition-all"
                              style={{
                                width: `${src.contribution_pct}%`,
                                backgroundColor: SOURCE_COLORS[src.source_type] ?? "#64748b",
                              }}
                            />
                          </div>
                        </div>
                      ));
                  })()}
                </div>
              </div>
            </div>
          )}

          {/* Ward map + forecast side by side */}
          <div className="grid lg:grid-cols-2 gap-4 mb-4">
            {/* Ward AQI map */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden" style={{ height: 340 }}>
              <div className="px-4 pt-3 pb-2 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-200">Ward AQI Map</p>
                  <p className="text-xs text-slate-500">Click a ward to view details</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowTraffic((v) => !v)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                      showTraffic
                        ? "bg-orange-500/20 border-orange-500/40 text-orange-300"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    🚗 Traffic
                  </button>
                  <button
                    onClick={() => setShowSatellite((v) => !v)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                      showSatellite
                        ? "bg-sky-500/20 border-sky-500/40 text-sky-300"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    🛰 Satellite AOD
                  </button>
                </div>
              </div>
              <div style={{ height: 290 }}>
                {wards.length > 0 ? (
                  <WardMap
                    wards={wards}
                    onWardClick={(wardId) => navigate(`/wards/${wardId}`)}
                    fireHotspots={fireHotspots}
                    trafficSegments={trafficSegments}
                    center={mapCenter}
                    showSatellite={showSatellite}
                    showTraffic={showTraffic}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-600 text-sm">
                    {selectedCityId ? "Loading wards…" : "Select a city"}
                  </div>
                )}
              </div>
            </div>

            {/* Forecast chart */}
            {forecastLoading || !selectedCityId ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex items-center justify-center min-h-64">
                <div className="text-center text-slate-600">
                  <p className="text-4xl mb-3">📈</p>
                  <p className="text-sm font-medium">
                    {selectedCityId ? "Loading forecast…" : "Select a city to see the forecast"}
                  </p>
                </div>
              </div>
            ) : forecast ? (
              <ForecastChart
                points={forecast.points}
                generatedAt={forecast.generated_at}
                peakAqi={forecast.peak_aqi}
              />
            ) : null}
          </div>
          {/* AQI Alerts */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-semibold text-slate-200">AQI Alerts</p>
                <p className="text-xs text-slate-500 mt-0.5">Recent threshold breaches</p>
              </div>
              {alerts.some((a) => a.is_active) && (
                <span className="flex items-center gap-1.5 text-xs font-semibold text-red-400 bg-red-500/10 px-2 py-1 rounded">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                  Active
                </span>
              )}
            </div>
            {alerts.length === 0 ? (
              <p className="text-sm text-slate-600 py-4 text-center">No recent alerts</p>
            ) : (
              <div className="space-y-2">
                {alerts.map((alert) => {
                  const levelColor =
                    alert.alert_level === "critical" ? "text-red-400 bg-red-500/10 border-red-500/20"
                    : alert.alert_level === "warning" ? "text-orange-400 bg-orange-500/10 border-orange-500/20"
                    : "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
                  return (
                    <div
                      key={alert.id}
                      className={`flex items-center justify-between rounded-lg border px-3 py-2.5 ${levelColor}`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">
                          {alert.alert_level === "critical" ? "🚨" : "⚠️"}
                        </span>
                        <div>
                          <p className="text-xs font-semibold capitalize">{alert.alert_level} — AQI {alert.aqi_value}</p>
                          <p className="text-xs opacity-70 mt-0.5">
                            {alert.dominant_source ? `Source: ${alert.dominant_source} · ` : ""}
                            {new Date(alert.triggered_at).toLocaleString("en-IN", {
                              timeZone: "Asia/Kolkata",
                              hour12: true,
                              day: "numeric",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                      </div>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${alert.is_active ? "bg-red-500/20 text-red-300" : "bg-slate-700 text-slate-400"}`}>
                        {alert.is_active ? "Active" : "Resolved"}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          {/* Satellite vs Ground Station comparison */}
          {(latestSat || satelliteObs.length > 0) && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mt-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-slate-200">🛰 Satellite vs Ground Station</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    MODIS Terra AOD → estimated PM2.5 vs CAAQMS ground readings
                    {latestSat?.is_mock && (
                      <span className="ml-2 text-slate-600">(mock — set EARTHDATA_TOKEN for real data)</span>
                    )}
                  </p>
                </div>
                {latestSat && (
                  <span className="text-xs text-slate-500">
                    Latest: {latestSat.observed_date}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                {/* Satellite AOD */}
                <div className="bg-slate-800 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">AOD (550nm)</p>
                  <p className={`text-2xl font-bold font-mono ${
                    latestSat?.aod_value == null ? "text-slate-500"
                    : latestSat.aod_value >= 0.6 ? "text-red-400"
                    : latestSat.aod_value >= 0.4 ? "text-orange-400"
                    : latestSat.aod_value >= 0.2 ? "text-yellow-400"
                    : "text-green-400"
                  }`}>
                    {latestSat?.aod_value != null ? latestSat.aod_value.toFixed(3) : "—"}
                  </p>
                  <p className="text-xs text-slate-600 mt-0.5">unitless</p>
                </div>

                {/* Satellite-estimated PM2.5 */}
                <div className="bg-slate-800 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">Sat. PM2.5 est.</p>
                  <p className="text-2xl font-bold font-mono text-sky-400">
                    {latestSat?.estimated_pm25 != null ? latestSat.estimated_pm25.toFixed(1) : "—"}
                  </p>
                  <p className="text-xs text-slate-600 mt-0.5">µg/m³ (AOD×120)</p>
                </div>

                {/* Ground PM2.5 */}
                <div className="bg-slate-800 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">Ground PM2.5</p>
                  <p className="text-2xl font-bold font-mono text-slate-200">
                    {attribution?.pollutant_snapshot?.pm25 != null
                      ? attribution.pollutant_snapshot.pm25.toFixed(1)
                      : "—"}
                  </p>
                  <p className="text-xs text-slate-600 mt-0.5">µg/m³ (CAAQMS)</p>
                </div>

                {/* Bias */}
                <div className="bg-slate-800 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">Sat − Ground bias</p>
                  {latestSat?.estimated_pm25 != null && attribution?.pollutant_snapshot?.pm25 != null ? (() => {
                    const bias = latestSat.estimated_pm25! - attribution.pollutant_snapshot!.pm25!;
                    return (
                      <>
                        <p className={`text-2xl font-bold font-mono ${bias > 10 ? "text-red-400" : bias < -10 ? "text-blue-400" : "text-green-400"}`}>
                          {bias > 0 ? "+" : ""}{bias.toFixed(1)}
                        </p>
                        <p className="text-xs text-slate-600 mt-0.5">
                          {Math.abs(bias) < 10 ? "Good agreement" : bias > 0 ? "Sat overestimate" : "Sat underestimate"}
                        </p>
                      </>
                    );
                  })() : (
                    <p className="text-2xl font-bold font-mono text-slate-500">—</p>
                  )}
                </div>
              </div>

              {/* 7-day AOD trend mini-bars */}
              {satelliteObs.length > 1 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">7-day AOD trend</p>
                  <div className="flex items-end gap-1 h-12">
                    {[...satelliteObs].reverse().map((obs) => {
                      const pct = Math.min(100, ((obs.aod_value ?? 0) / 1.0) * 100);
                      const barColor = (obs.aod_value ?? 0) >= 0.6 ? "bg-red-500"
                        : (obs.aod_value ?? 0) >= 0.4 ? "bg-orange-400"
                        : (obs.aod_value ?? 0) >= 0.2 ? "bg-yellow-400"
                        : "bg-green-500";
                      return (
                        <div key={obs.observed_date} className="flex-1 flex flex-col items-center gap-1" title={`${obs.observed_date}: AOD ${obs.aod_value?.toFixed(3) ?? "—"}`}>
                          <div className="w-full flex items-end justify-center" style={{ height: 40 }}>
                            <div
                              className={`w-full rounded-sm ${barColor} opacity-80`}
                              style={{ height: `${Math.max(4, pct)}%` }}
                            />
                          </div>
                          <span className="text-slate-600" style={{ fontSize: 8 }}>
                            {obs.observed_date.slice(5)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
          {/* Traffic congestion panel */}
          {trafficSegments.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mt-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-slate-200">🚗 Live Traffic Congestion</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    TomTom Flow API — congestion ratio = free-flow / current speed
                    {trafficSegments[0]?.is_mock && (
                      <span className="ml-2 text-slate-600">(mock — set TOMTOM_API_KEY for live)</span>
                    )}
                  </p>
                </div>
                <div className="text-right">
                  {avgCongestion != null && (
                    <span className={`text-sm font-bold font-mono ${
                      avgCongestion >= 2.5 ? "text-red-400"
                      : avgCongestion >= 1.5 ? "text-orange-400"
                      : "text-green-400"
                    }`}>
                      {avgCongestion.toFixed(2)}× avg
                    </span>
                  )}
                  {heavySegments > 0 && (
                    <p className="text-xs text-red-400 mt-0.5">{heavySegments} heavily congested</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                {trafficSegments.map((seg) => {
                  const pct = Math.min(100, (seg.congestion_ratio / 4.0) * 100);
                  const color = seg.congestion_ratio >= 2.5 ? "bg-red-500"
                    : seg.congestion_ratio >= 1.5 ? "bg-orange-400"
                    : seg.congestion_ratio >= 1.0 ? "bg-lime-500"
                    : "bg-green-500";
                  const label = seg.congestion_ratio >= 2.5 ? "Heavy"
                    : seg.congestion_ratio >= 1.5 ? "Moderate"
                    : seg.congestion_ratio >= 1.0 ? "Normal"
                    : "Clear";
                  return (
                    <div key={seg.segment_id} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-44 truncate flex-shrink-0" title={seg.segment_name ?? seg.segment_id}>
                        {seg.segment_name ?? seg.segment_id}
                      </span>
                      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs font-mono text-slate-300 w-10 text-right flex-shrink-0">
                        {seg.congestion_ratio.toFixed(2)}×
                      </span>
                      <span className={`text-xs w-16 flex-shrink-0 ${
                        label === "Heavy" ? "text-red-400"
                        : label === "Moderate" ? "text-orange-400"
                        : label === "Normal" ? "text-lime-400"
                        : "text-green-400"
                      }`}>{label}</span>
                    </div>
                  );
                })}
              </div>

              {avgCongestion != null && avgCongestion > 1.5 && (
                <p className="text-xs text-orange-400/70 mt-3 border-t border-slate-800 pt-2">
                  ⚡ Congestion signal active — vehicular attribution weight boosted by{" "}
                  {Math.round(Math.min((avgCongestion - 1.5) / 1.5, 1.0) * 15)}% in attribution engine
                </p>
              )}
            </div>
          )}
        </main>
    </div>
  );
}
