import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid } from "recharts";
import { fetchWardDetail, fetchWardForecast } from "@/features/wards/api";
import { useCities } from "@/features/cities/useCities";

const PIE_COLORS: Record<string, string> = {
  vehicular_pct: "#f97316",
  industrial_pct: "#8b5cf6",
  construction_pct: "#eab308",
  agricultural_pct: "#22c55e",
  fire_pct: "#ef4444",
  other_pct: "#94a3b8",
};

const SOURCE_LABELS: Record<string, string> = {
  vehicular_pct: "Vehicular",
  industrial_pct: "Industrial",
  construction_pct: "Construction",
  agricultural_pct: "Agricultural",
  fire_pct: "Fire",
  other_pct: "Other",
};

function vulnBadgeClass(tier: string): string {
  switch (tier) {
    case "Critical": return "bg-red-600 text-white";
    case "High":     return "bg-orange-500 text-white";
    case "Moderate": return "bg-yellow-500 text-slate-900";
    default:         return "bg-green-600 text-white";
  }
}

function aqiBadgeClass(aqi: number | null): string {
  if (!aqi) return "bg-slate-500";
  if (aqi <= 50) return "bg-green-500";
  if (aqi <= 100) return "bg-lime-500";
  if (aqi <= 200) return "bg-yellow-500";
  if (aqi <= 300) return "bg-orange-500";
  if (aqi <= 400) return "bg-red-500";
  return "bg-purple-600";
}

export default function WardDetail() {
  const { id: wardId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { selectedCityId } = useCities();

  const { data: ward, isLoading, isError } = useQuery({
    queryKey: ["ward-detail", selectedCityId, wardId],
    queryFn: () => fetchWardDetail(selectedCityId!, wardId!),
    enabled: !!selectedCityId && !!wardId,
  });

  const { data: wardForecast } = useQuery({
    queryKey: ["ward-forecast", selectedCityId, wardId],
    queryFn: () => fetchWardForecast(selectedCityId!, wardId!),
    enabled: !!selectedCityId && !!wardId,
    staleTime: 1000 * 60 * 15,
  });

  if (!selectedCityId) {
    return (
      <div className="p-8 text-slate-300">
        No city selected. Return to{" "}
        <button className="underline text-sky-400" onClick={() => navigate("/dashboard")}>
          Dashboard
        </button>
        .
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-8 text-slate-400">Loading ward details…</div>;
  }

  if (isError || !ward) {
    return (
      <div className="p-8 text-red-400">
        Ward not found.{" "}
        <button className="underline text-sky-400" onClick={() => navigate(-1)}>
          Go back
        </button>
        .
      </div>
    );
  }

  const pieData = Object.entries(ward.attribution_breakdown)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: SOURCE_LABELS[key] ?? key,
      value: Math.round(value * 10) / 10,
      color: PIE_COLORS[key] ?? "#94a3b8",
    }));

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Top bar */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate("/dashboard")}
          className="text-sky-400 hover:text-sky-300 text-sm"
        >
          ← Dashboard
        </button>
        <h1 className="text-xl font-bold">{ward.name}</h1>
        <span className="text-slate-400 text-sm">Ward Detail</span>
      </div>

      <div className="p-6 max-w-6xl mx-auto space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Current AQI</p>
            <div className="flex items-center gap-2">
              <span
                className={`text-2xl font-bold px-2 py-0.5 rounded ${aqiBadgeClass(ward.avg_aqi)} text-white`}
              >
                {ward.avg_aqi ?? "—"}
              </span>
            </div>
            {ward.aqi_category && (
              <p className="text-slate-400 text-xs mt-1">{ward.aqi_category}</p>
            )}
          </div>

          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Population</p>
            <p className="text-2xl font-bold">
              {ward.population ? ward.population.toLocaleString() : "—"}
            </p>
          </div>

          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Dominant Source</p>
            <p className="text-lg font-semibold capitalize">
              {ward.dominant_source ?? "—"}
            </p>
          </div>

          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">
              Advisories (ward)
            </p>
            <p className="text-2xl font-bold">{ward.advisory_count}</p>
          </div>

          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Vulnerability</p>
            {ward.vulnerable_site_flags?.vulnerability_tier ? (
              <div className="space-y-1">
                <span
                  className={`inline-block text-xs font-bold px-2 py-1 rounded ${vulnBadgeClass(
                    ward.vulnerable_site_flags.vulnerability_tier as string
                  )}`}
                >
                  {ward.vulnerable_site_flags.vulnerability_tier as string}
                </span>
                <p className="text-slate-400 text-xs">
                  Score:{" "}
                  <span className="font-mono text-slate-200">
                    {(ward.vulnerable_site_flags.vulnerability_score as number).toFixed(2)}
                  </span>
                </p>
                <p className="text-slate-500 text-xs">population × AQI exposure</p>
              </div>
            ) : (
              <p className="text-slate-500 text-sm mt-1">Pending next refresh</p>
            )}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Attribution pie chart */}
          <div className="bg-slate-800 rounded-xl p-4">
            <h2 className="font-semibold mb-3 text-slate-200">
              Pollution Source Attribution
              <span className="ml-2 text-xs text-sky-500">(chemical fingerprint + wind)</span>
            </h2>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, value }) => `${name} ${value}%`}
                    labelLine={false}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-slate-500 text-sm py-8 text-center">
                No attribution data — run attribution compute first.
              </p>
            )}
          </div>

          {/* Station readings table */}
          <div className="bg-slate-800 rounded-xl p-4">
            <h2 className="font-semibold mb-3 text-slate-200">Station Readings</h2>
            {ward.station_readings.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 text-xs border-b border-slate-700">
                      <th className="text-left pb-2">Station</th>
                      <th className="text-right pb-2">AQI</th>
                      <th className="text-right pb-2">PM2.5 µg/m³</th>
                      <th className="text-right pb-2">PM10 µg/m³</th>
                      <th className="text-left pb-2 pl-2">Category</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ward.station_readings.map((r) => (
                      <tr key={r.station_id} className="border-b border-slate-700/50">
                        <td className="py-2 text-slate-300">
                          {r.station_name ?? r.station_id}
                          {r.is_stale && (
                            <span
                              className="ml-1.5 text-xs text-amber-500"
                              title="Sensor offline — no recent data"
                            >
                              ⚠ offline
                            </span>
                          )}
                        </td>
                        <td className="py-2 text-right font-mono font-bold">
                          {r.is_stale ? <span title="Sensor offline" className="text-slate-600">—</span> : (r.aqi ?? "—")}
                        </td>
                        <td className="py-2 text-right font-mono text-slate-300">
                          {r.is_stale ? <span title="Sensor offline" className="text-slate-600">—</span> : (r.pm25 != null ? r.pm25.toFixed(1) : "—")}
                        </td>
                        <td className="py-2 text-right font-mono text-slate-300">
                          {r.is_stale ? <span title="Sensor offline" className="text-slate-600">—</span> : (r.pm10 != null ? r.pm10.toFixed(1) : "—")}
                        </td>
                        <td className="py-2 pl-2 text-slate-400 text-xs">
                          {r.is_stale ? <span title="Sensor offline" className="text-slate-600">—</span> : (r.aqi_category ?? "—")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-slate-500 text-sm py-8 text-center">
                No stations assigned to this ward.
              </p>
            )}
          </div>
        </div>

        {/* 72h Hyperlocal Forecast */}
        <div className="bg-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold text-slate-200">72h Hyperlocal AQI Forecast</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                ward-hyperlocal-v1 · Open-Meteo forward wind · emission-source proximity
              </p>
            </div>
            {wardForecast && (
              <div className="text-right">
                <p className="text-xs text-slate-500">Peak forecast</p>
                <span className={`text-lg font-bold ${aqiBadgeClass(wardForecast.peak_aqi)} px-2 py-0.5 rounded text-white`}>
                  {wardForecast.peak_aqi}
                </span>
              </div>
            )}
          </div>

          {wardForecast && wardForecast.points.length > 0 ? (() => {
            // Sample every 2h for readability (36 points from 72)
            const chartData = wardForecast.points
              .filter((_, i) => i % 2 === 0)
              .map((p) => ({
                label: new Date(p.forecast_for_ts).toLocaleString("en-IN", { month: "short", day: "numeric", hour: "2-digit", hour12: false }),
                aqi: p.predicted_aqi,
                pm25: p.predicted_pm25 != null ? Math.round(p.predicted_pm25 * 10) / 10 : null,
                conf: p.confidence != null ? Math.round(p.confidence * 100) : null,
              }));

            const maxAqi = Math.max(...chartData.map((d) => d.aqi));
            const fillColor = maxAqi > 300 ? "#ef4444" : maxAqi > 200 ? "#f97316" : maxAqi > 100 ? "#eab308" : "#22c55e";

            return (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="wardAqiGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={fillColor} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={fillColor} stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} interval={5} />
                  <YAxis domain={[0, 500]} tick={{ fill: "#94a3b8", fontSize: 10 }} width={36} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                    labelStyle={{ color: "#cbd5e1", fontSize: 11 }}
                    formatter={(val: number, name: string) => [
                      name === "aqi" ? `${val} AQI` : `${val} µg/m³`,
                      name === "aqi" ? "AQI" : "PM2.5",
                    ]}
                  />
                  <Area type="monotone" dataKey="aqi" stroke={fillColor} fill="url(#wardAqiGrad)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            );
          })() : (
            <p className="text-slate-500 text-sm py-8 text-center">Loading forecast…</p>
          )}
        </div>
      </div>
    </div>
  );
}
