import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer,
} from "recharts";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import { fetchReportSummary, fetchAqiTrend } from "@/features/reports/api";
import type { WardAqiRow, EnforcementStats } from "@/features/reports/api";


const PERIOD_OPTIONS = [
  { label: "Last 7 days", value: 7 },
  { label: "Last 30 days", value: 30 },
  { label: "Last 90 days", value: 90 },
];

function aqiColor(aqi: number | null): string {
  if (aqi === null) return "text-slate-400";
  if (aqi <= 50) return "text-green-400";
  if (aqi <= 100) return "text-lime-400";
  if (aqi <= 200) return "text-yellow-400";
  if (aqi <= 300) return "text-orange-400";
  if (aqi <= 400) return "text-red-400";
  return "text-purple-400";
}

function aqiLabel(aqi: number | null): string {
  if (aqi === null) return "—";
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 flex flex-col gap-1">
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function EnforcementStatCard({ stats, days }: { stats: EnforcementStats; days: number }) {
  const total = stats.completed_total + stats.dispatched_active + stats.pending_count;
  const completionRate = total > 0 ? Math.round((stats.completed_total / total) * 100) : 0;
  return (
    <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 flex flex-col gap-2">
      <div className="text-xs text-slate-400 uppercase tracking-wide">Interventions Completed ({days}d)</div>
      <div className="text-2xl font-bold text-green-400">{stats.completed_period}</div>
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-slate-500">
          <span>Overall completion rate</span>
          <span className="text-slate-300 font-mono">{completionRate}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-green-500 transition-all"
            style={{ width: `${completionRate}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-500">
          <span>{stats.dispatched_active} dispatched · {stats.pending_count} pending</span>
        </div>
      </div>
    </div>
  );
}

function WardTable({ rows }: { rows: WardAqiRow[] }) {
  if (!rows.length) {
    return <p className="text-slate-500 text-sm">No ward data for this period.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-slate-400 text-left">
            <th className="py-2 pr-4">Ward</th>
            <th className="py-2 pr-4">Avg AQI</th>
            <th className="py-2 pr-4">Category</th>
            <th className="py-2">Readings</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ward_id} className="border-b border-slate-900 hover:bg-slate-900/50">
              <td className="py-2 pr-4 text-white font-medium">{row.ward_name}</td>
              <td className={`py-2 pr-4 font-semibold ${aqiColor(row.avg_aqi)}`}>
                {row.avg_aqi !== null ? Math.round(row.avg_aqi) : "—"}
              </td>
              <td className="py-2 pr-4 text-slate-300">{aqiLabel(row.avg_aqi)}</td>
              <td className="py-2 text-slate-400">{row.reading_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ReportsPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { selectedCityId } = useCities();
  const [days, setDays] = useState(7);

  const cityId = selectedCityId ?? user?.city_id ?? "";

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ["report-summary", cityId, days],
    queryFn: () => fetchReportSummary(cityId, days),
    enabled: !!cityId,
  });

  const { data: trendData = [] } = useQuery({
    queryKey: ["aqi-trend", cityId, days],
    queryFn: () => fetchAqiTrend(cityId, days),
    enabled: !!cityId,
    staleTime: 1000 * 60 * 15,
  });

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleDownloadCsv = async () => {
    if (!cityId) return;
    const token = localStorage.getItem("access_token") ?? "";
    const url = `/api/v1/cities/${cityId}/reports/summary.csv?days=${days}`;
    const resp = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = `vayushield-report-${cityId}-${days}d.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(href);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-950 text-white">
        {/* Topbar */}
        <header className="h-14 flex items-center justify-between px-6 border-b border-slate-800 bg-slate-900 flex-shrink-0">
          <div>
            <h1 className="text-base font-semibold text-white">Reports & Export</h1>
            {summary && (
              <p className="text-xs text-slate-400">{summary.city.name}, {summary.city.state}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Period selector */}
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="text-sm bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              {PERIOD_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <button
              onClick={handleDownloadCsv}
              disabled={!summary}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              ⬇ Download CSV
            </button>
            <button
              onClick={handleLogout}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {!cityId && (
            <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-xl p-4 text-yellow-300 text-sm">
              No city selected. Please select a city from the Dashboard.
            </div>
          )}

          {isLoading && (
            <div className="text-slate-400 text-sm">Loading report…</div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 text-red-300 text-sm">
              Failed to load report. You may not have access to this city.
            </div>
          )}

          {summary && (
            <>
              {/* Summary stat cards */}
              <section>
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
                  Air Quality Overview
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {summary.enforcement_stats && (
                    <EnforcementStatCard stats={summary.enforcement_stats} days={days} />
                  )}
                  <StatCard
                    label="City AQI (Max Station)"
                    value={
                      summary.aqi_stats.current_avg_aqi !== null
                        ? Math.round(summary.aqi_stats.current_avg_aqi).toString()
                        : "—"
                    }
                    sub={aqiLabel(summary.aqi_stats.current_avg_aqi)}
                  />
                  <StatCard
                    label={`Peak AQI (${days}d)`}
                    value={
                      summary.aqi_stats.peak_aqi_7d !== null
                        ? Math.round(summary.aqi_stats.peak_aqi_7d).toString()
                        : "—"
                    }
                    sub={aqiLabel(summary.aqi_stats.peak_aqi_7d)}
                  />
                  <StatCard
                    label="Forecast Peak (24h)"
                    value={
                      summary.forecast.next_24h_peak_aqi !== null
                        ? Math.round(summary.forecast.next_24h_peak_aqi).toString()
                        : "—"
                    }
                    sub={
                      summary.forecast.dominant_hour !== null
                        ? `Peak at ${summary.forecast.dominant_hour}:00 UTC`
                        : undefined
                    }
                  />
                  <StatCard
                    label="Dominant Source"
                    value={summary.attribution.dominant_source ?? "Unknown"}
                  />
                </div>
              </section>

              {/* AQI Category breakdown */}
              <section>
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
                  AQI Category Breakdown (% of Hours)
                </h2>
                <div className="bg-gray-800 rounded-xl border border-slate-800 p-4 space-y-2">
                  {Object.entries(summary.aqi_stats.category_breakdown).map(([cat, pct]) => (
                    <div key={cat} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-24 flex-shrink-0">{cat}</span>
                      <div className="flex-1 bg-slate-800 rounded-full h-2">
                        <div
                          className="h-2 rounded-full bg-sky-500"
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-300 w-12 text-right">{pct.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* Top enforcement items + advisory counts side-by-side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <section>
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Top Enforcement Priorities
                  </h2>
                  <div className="bg-gray-800 rounded-xl border border-slate-800 divide-y divide-gray-700">
                    {summary.top_enforcement_items.length === 0 && (
                      <p className="p-4 text-sm text-slate-500">No enforcement items.</p>
                    )}
                    {summary.top_enforcement_items.map((item, i) => (
                      <div key={item.id} className="p-4 flex items-center gap-3">
                        <span className="text-lg font-bold text-gray-600">#{i + 1}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white font-medium truncate">{item.source_name}</div>
                          <div className="text-xs text-slate-500 capitalize">{item.source_type}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-orange-400">
                            {(item.priority_score * 100).toFixed(0)}
                          </div>
                          <div className="text-xs text-slate-500 capitalize">{item.status}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Advisories by Language
                  </h2>
                  <div className="bg-gray-800 rounded-xl border border-slate-800 p-4 space-y-2">
                    {Object.keys(summary.advisory_count_by_language).length === 0 && (
                      <p className="text-sm text-slate-500">No advisories generated yet.</p>
                    )}
                    {Object.entries(summary.advisory_count_by_language).map(([lang, count]) => (
                      <div key={lang} className="flex justify-between text-sm">
                        <span className="text-slate-300 uppercase">{lang}</span>
                        <span className="text-white font-semibold">{count}</span>
                      </div>
                    ))}
                  </div>

                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mt-4 mb-3">
                    Attribution Breakdown
                  </h2>
                  <div className="bg-gray-800 rounded-xl border border-slate-800 p-4 space-y-2">
                    {Object.entries(summary.attribution.breakdown).map(([src, pct]) => (
                      <div key={src} className="flex justify-between text-sm">
                        <span className="text-slate-300 capitalize">{src}</span>
                        <span className="text-white font-semibold">{pct.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              {/* 7-day AQI trend chart */}
              {trendData.length > 0 && (
                <section>
                  <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    AQI Trend — Last {days} Days (Hourly)
                  </h2>
                  <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
                    <ResponsiveContainer width="100%" height={220}>
                      <AreaChart
                        data={trendData.map((p) => ({
                          label: new Date(p.hour).toLocaleDateString("en-IN", {
                            month: "short", day: "numeric", hour: "2-digit", hour12: false,
                          }),
                          aqi: p.aqi,
                        }))}
                        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                      >
                        <defs>
                          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.35} />
                            <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        {/* AQI category band lines */}
                        <ReferenceLine y={50}  stroke="#22c55e" strokeDasharray="3 3" strokeOpacity={0.4} label={{ value: "Good", fill: "#22c55e", fontSize: 9, position: "insideTopLeft" }} />
                        <ReferenceLine y={100} stroke="#a3e635" strokeDasharray="3 3" strokeOpacity={0.4} label={{ value: "Satisfactory", fill: "#a3e635", fontSize: 9, position: "insideTopLeft" }} />
                        <ReferenceLine y={200} stroke="#eab308" strokeDasharray="3 3" strokeOpacity={0.4} label={{ value: "Moderate", fill: "#eab308", fontSize: 9, position: "insideTopLeft" }} />
                        <ReferenceLine y={300} stroke="#f97316" strokeDasharray="3 3" strokeOpacity={0.4} label={{ value: "Poor", fill: "#f97316", fontSize: 9, position: "insideTopLeft" }} />
                        <ReferenceLine y={400} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.4} label={{ value: "Very Poor", fill: "#ef4444", fontSize: 9, position: "insideTopLeft" }} />
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis
                          dataKey="label"
                          tick={{ fill: "#64748b", fontSize: 10 }}
                          interval={Math.floor(trendData.length / 8)}
                        />
                        <YAxis domain={[0, 500]} tick={{ fill: "#64748b", fontSize: 10 }} width={36} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }}
                          labelStyle={{ color: "#94a3b8", fontSize: 11 }}
                          formatter={(v: number) => [`${v} AQI`, "Avg AQI"]}
                        />
                        <Area
                          type="monotone"
                          dataKey="aqi"
                          stroke="#38bdf8"
                          fill="url(#trendGrad)"
                          strokeWidth={1.5}
                          dot={false}
                          activeDot={{ r: 3, fill: "#38bdf8" }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              )}

              {/* Per-ward AQI table */}
              <section>
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
                  Per-Ward Avg AQI — Last {days} Days
                </h2>
                <div className="bg-gray-800 rounded-xl border border-slate-800 p-4">
                  <WardTable rows={summary.ward_aqi_table} />
                </div>
              </section>
            </>
          )}
        </main>
    </div>
  );
}
