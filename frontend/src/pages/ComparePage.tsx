import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, AreaChart, Area,
} from "recharts";
import client from "@/lib/apiClient";

// ── Types ─────────────────────────────────────────────────────────────────────

interface CitySnapshot {
  city_id: string;
  city_name: string;
  current_aqi: number | null;
  aqi_category: string | null;
  trend_delta: number | null;
  peak_forecast_aqi: number | null;
  dominant_source: string | null;
  attribution_confidence: number | null;
  pending_enforcement: number;
  dispatched_enforcement: number;
  completed_enforcement: number;
  intervention_effectiveness: number | null;
  aqi_history_24h: { hour: string; aqi: number }[];
}

interface CompareOut {
  generated_at: string;
  cities: CitySnapshot[];
}

async function fetchCompare(): Promise<CompareOut> {
  const resp = await client.get<{ data: CompareOut }>("/cities/compare");
  return resp.data.data!;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const CITY_COLORS: Record<string, string> = {
  Delhi: "#f97316",
  Mumbai: "#3b82f6",
  Bengaluru: "#22c55e",
};

function aqiBg(aqi: number | null): string {
  if (!aqi) return "bg-slate-700";
  if (aqi <= 50)  return "bg-green-500";
  if (aqi <= 100) return "bg-lime-500";
  if (aqi <= 200) return "bg-yellow-500";
  if (aqi <= 300) return "bg-orange-500";
  if (aqi <= 400) return "bg-red-500";
  return "bg-purple-600";
}

function aqiText(aqi: number | null): string {
  if (!aqi) return "text-slate-400";
  if (aqi <= 50)  return "text-green-400";
  if (aqi <= 100) return "text-lime-400";
  if (aqi <= 200) return "text-yellow-400";
  if (aqi <= 300) return "text-orange-400";
  if (aqi <= 400) return "text-red-400";
  return "text-purple-400";
}

function TrendArrow({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-slate-500">—</span>;
  if (Math.abs(delta) < 5) return <span className="text-slate-400">→ stable</span>;
  if (delta > 0) return <span className="text-red-400">↑ +{delta} worsening</span>;
  return <span className="text-green-400">↓ {delta} improving</span>;
}

function SourceBadge({ source }: { source: string | null }) {
  if (!source) return <span className="text-slate-500">—</span>;
  const colors: Record<string, string> = {
    industrial: "bg-purple-500/20 text-purple-300",
    vehicular: "bg-orange-500/20 text-orange-300",
    agricultural: "bg-lime-500/20 text-lime-300",
    construction: "bg-yellow-500/20 text-yellow-300",
    fire: "bg-red-500/20 text-red-300",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold capitalize ${colors[source] ?? "bg-slate-700 text-slate-300"}`}>
      {source}
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function ComparePage() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ["cities-compare"],
    queryFn: fetchCompare,
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-400 flex items-center justify-center">
        Loading city comparison…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-slate-950 text-red-400 flex items-center justify-center">
        Failed to load comparison data.
      </div>
    );
  }

  const cities = data.cities;

  // Build merged 24h history for multi-line chart
  // Normalize to hour offset (0 = oldest, 23 = newest) for alignment
  const allHours = Array.from(
    new Set(cities.flatMap((c) => c.aqi_history_24h.map((h) => h.hour)))
  ).sort();

  const mergedHistory = allHours.map((hour) => {
    const entry: Record<string, number | string> = {
      label: new Date(hour).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false }),
    };
    for (const city of cities) {
      const point = city.aqi_history_24h.find((h) => h.hour === hour);
      if (point) entry[city.city_name] = point.aqi;
    }
    return entry;
  });

  const generatedAt = new Date(data.generated_at).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", hour12: true,
  });

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate("/dashboard")} className="text-sky-400 hover:text-sky-300 text-sm">
            ← Dashboard
          </button>
          <div>
            <h1 className="text-lg font-bold">Multi-City Comparison</h1>
            <p className="text-xs text-slate-500">Updated {generatedAt} · {cities.length} cities</p>
          </div>
        </div>
        <span className="flex items-center gap-2 text-sm text-slate-400">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          Live data
        </span>
      </div>

      <div className="p-6 max-w-7xl mx-auto space-y-6">

        {/* City AQI cards */}
        <div className="grid md:grid-cols-3 gap-4">
          {cities.map((city) => (
            <div key={city.city_id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{city.city_name}</p>
                  <div className="flex items-center gap-2">
                    <span className={`text-4xl font-bold ${aqiText(city.current_aqi)}`}>
                      {city.current_aqi ?? "—"}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-semibold text-white ${aqiBg(city.current_aqi)}`}>
                      {city.aqi_category ?? "—"}
                    </span>
                  </div>
                </div>
                <div
                  className="w-3 h-3 rounded-full mt-1"
                  style={{ backgroundColor: CITY_COLORS[city.city_name] ?? "#94a3b8" }}
                />
              </div>

              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">6h trend</span>
                  <TrendArrow delta={city.trend_delta} />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">72h peak forecast</span>
                  <span className={`font-mono font-bold ${aqiText(city.peak_forecast_aqi)}`}>
                    {city.peak_forecast_aqi ?? "—"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Dominant source</span>
                  <SourceBadge source={city.dominant_source} />
                </div>
                {city.attribution_confidence != null && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Attribution confidence</span>
                    <span className="text-slate-300 text-xs">{Math.round(city.attribution_confidence * 100)}%</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* 24h AQI trend chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="font-semibold text-slate-200 mb-1">24h AQI Trend</h2>
          <p className="text-xs text-slate-500 mb-4">Hourly city-average AQI over the past 24 hours</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={mergedHistory} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} interval={3} />
              <YAxis domain={[0, 500]} tick={{ fill: "#64748b", fontSize: 10 }} width={36} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }}
                labelStyle={{ color: "#94a3b8", fontSize: 11 }}
              />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
              {/* AQI bands */}
              {[{ y: 100, label: "Satisfactory" }, { y: 200, label: "Moderate" }, { y: 300, label: "Poor" }].map(({ y }) => (
                <Line key={y} dataKey={() => y} dot={false} strokeDasharray="4 4" stroke="#334155" strokeWidth={1} legendType="none" />
              ))}
              {cities.map((city) => (
                <Line
                  key={city.city_id}
                  type="monotone"
                  dataKey={city.city_name}
                  stroke={CITY_COLORS[city.city_name] ?? "#94a3b8"}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Enforcement + intervention table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="font-semibold text-slate-200 mb-1">Intervention Effectiveness</h2>
          <p className="text-xs text-slate-500 mb-4">Enforcement actions by city</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-xs uppercase border-b border-slate-800">
                <th className="text-left pb-2 pr-4">City</th>
                <th className="text-right pb-2 pr-4">Pending</th>
                <th className="text-right pb-2 pr-4">Dispatched</th>
                <th className="text-right pb-2 pr-4">Completed</th>
                <th className="text-right pb-2 pr-4">Effectiveness</th>
                <th className="pb-2">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {cities.map((city) => {
                const eff = city.intervention_effectiveness;
                const pct = eff != null ? Math.round(eff * 100) : 0;
                const total = city.pending_enforcement + city.dispatched_enforcement + city.completed_enforcement;
                return (
                  <tr key={city.city_id}>
                    <td className="py-3 pr-4">
                      <span className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: CITY_COLORS[city.city_name] ?? "#94a3b8" }}
                        />
                        {city.city_name}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-right font-mono text-orange-400">{city.pending_enforcement}</td>
                    <td className="py-3 pr-4 text-right font-mono text-sky-400">{city.dispatched_enforcement}</td>
                    <td className="py-3 pr-4 text-right font-mono text-green-400">{city.completed_enforcement}</td>
                    <td className="py-3 pr-4 text-right font-mono">
                      {eff != null ? (
                        <span className={eff >= 0.5 ? "text-green-400" : eff >= 0.2 ? "text-yellow-400" : "text-red-400"}>
                          {pct}%
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-3 w-40">
                      {total > 0 ? (
                        <div className="flex h-2 rounded-full overflow-hidden bg-slate-800 gap-px">
                          <div className="bg-green-500" style={{ width: `${(city.completed_enforcement / total) * 100}%` }} />
                          <div className="bg-sky-500" style={{ width: `${(city.dispatched_enforcement / total) * 100}%` }} />
                          <div className="bg-orange-500" style={{ width: `${(city.pending_enforcement / total) * 100}%` }} />
                        </div>
                      ) : (
                        <div className="h-2 rounded-full bg-slate-800" />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="flex gap-4 mt-3 text-xs text-slate-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-500" /> Completed</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-sky-500" /> Dispatched</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-orange-500" /> Pending</span>
          </div>
        </div>

        {/* Source attribution comparison */}
        <div className="grid md:grid-cols-3 gap-4">
          {cities.map((city) => (
            <div key={city.city_id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{city.city_name}</p>
              <p className="font-semibold text-slate-200 mb-3">Source Attribution</p>
              <div className="flex items-center gap-3">
                <SourceBadge source={city.dominant_source} />
                <span className="text-slate-400 text-sm">dominant</span>
              </div>
              {city.attribution_confidence != null && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-slate-500 mb-1">
                    <span>Confidence</span>
                    <span>{Math.round(city.attribution_confidence * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-sky-500 rounded-full"
                      style={{ width: `${Math.round(city.attribution_confidence * 100)}%` }}
                    />
                  </div>
                </div>
              )}
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-800 rounded p-2">
                  <p className="text-slate-500">Peak 72h</p>
                  <p className={`font-mono font-bold ${aqiText(city.peak_forecast_aqi)}`}>
                    {city.peak_forecast_aqi ?? "—"}
                  </p>
                </div>
                <div className="bg-slate-800 rounded p-2">
                  <p className="text-slate-500">6h trend</p>
                  <TrendArrow delta={city.trend_delta} />
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
