import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import { fetchReportSummary } from "@/features/reports/api";
import type { WardAqiRow } from "@/features/reports/api";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/enforcement", label: "Enforcement", icon: "🚨" },
  { to: "/advisories", label: "Advisories", icon: "📢" },
  { to: "/reports", label: "Reports", icon: "📄" },
  { to: "/admin/cities", label: "City Admin", icon: "🏙️" },
];

const PERIOD_OPTIONS = [
  { label: "Last 7 days", value: 7 },
  { label: "Last 30 days", value: 30 },
  { label: "Last 90 days", value: 90 },
];

function aqiColor(aqi: number | null): string {
  if (aqi === null) return "text-gray-400";
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
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 flex flex-col gap-1">
      <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

function WardTable({ rows }: { rows: WardAqiRow[] }) {
  if (!rows.length) {
    return <p className="text-gray-500 text-sm">No ward data for this period.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700 text-gray-400 text-left">
            <th className="py-2 pr-4">Ward</th>
            <th className="py-2 pr-4">Avg AQI</th>
            <th className="py-2 pr-4">Category</th>
            <th className="py-2">Readings</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ward_id} className="border-b border-gray-800 hover:bg-gray-800/50">
              <td className="py-2 pr-4 text-white font-medium">{row.ward_name}</td>
              <td className={`py-2 pr-4 font-semibold ${aqiColor(row.avg_aqi)}`}>
                {row.avg_aqi !== null ? Math.round(row.avg_aqi) : "—"}
              </td>
              <td className="py-2 pr-4 text-gray-300">{aqiLabel(row.avg_aqi)}</td>
              <td className="py-2 text-gray-400">{row.reading_count}</td>
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
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-700">
          <span className="text-lg font-bold text-sky-400">VayuShield</span>
          <span className="text-xs text-gray-500 block">AI Platform</span>
        </div>
        <nav className="flex-1 py-4 px-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-sky-600/20 text-sky-400"
                    : "text-gray-400 hover:bg-gray-700 hover:text-white"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-500">
          {user?.email}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-14 flex items-center justify-between px-6 border-b border-gray-700 bg-gray-800 flex-shrink-0">
          <div>
            <h1 className="text-base font-semibold text-white">Reports & Export</h1>
            {summary && (
              <p className="text-xs text-gray-400">{summary.city.name}, {summary.city.state}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Period selector */}
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="text-sm bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
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
              className="text-xs text-gray-400 hover:text-white transition-colors"
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
            <div className="text-gray-400 text-sm">Loading report…</div>
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
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                  Air Quality Overview
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="Current Avg AQI"
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
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                  AQI Category Breakdown (% of Hours)
                </h2>
                <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-2">
                  {Object.entries(summary.aqi_stats.category_breakdown).map(([cat, pct]) => (
                    <div key={cat} className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-24 flex-shrink-0">{cat}</span>
                      <div className="flex-1 bg-gray-700 rounded-full h-2">
                        <div
                          className="h-2 rounded-full bg-sky-500"
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-300 w-12 text-right">{pct.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* Top enforcement items + advisory counts side-by-side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <section>
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                    Top Enforcement Priorities
                  </h2>
                  <div className="bg-gray-800 rounded-xl border border-gray-700 divide-y divide-gray-700">
                    {summary.top_enforcement_items.length === 0 && (
                      <p className="p-4 text-sm text-gray-500">No enforcement items.</p>
                    )}
                    {summary.top_enforcement_items.map((item, i) => (
                      <div key={item.id} className="p-4 flex items-center gap-3">
                        <span className="text-lg font-bold text-gray-600">#{i + 1}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white font-medium truncate">{item.source_name}</div>
                          <div className="text-xs text-gray-500 capitalize">{item.source_type}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-orange-400">
                            {(item.priority_score * 100).toFixed(0)}
                          </div>
                          <div className="text-xs text-gray-500 capitalize">{item.status}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section>
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                    Advisories by Language
                  </h2>
                  <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-2">
                    {Object.keys(summary.advisory_count_by_language).length === 0 && (
                      <p className="text-sm text-gray-500">No advisories generated yet.</p>
                    )}
                    {Object.entries(summary.advisory_count_by_language).map(([lang, count]) => (
                      <div key={lang} className="flex justify-between text-sm">
                        <span className="text-gray-300 uppercase">{lang}</span>
                        <span className="text-white font-semibold">{count}</span>
                      </div>
                    ))}
                  </div>

                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mt-4 mb-3">
                    Attribution Breakdown
                  </h2>
                  <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-2">
                    {Object.entries(summary.attribution.breakdown).map(([src, pct]) => (
                      <div key={src} className="flex justify-between text-sm">
                        <span className="text-gray-300 capitalize">{src}</span>
                        <span className="text-white font-semibold">{pct.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              {/* Per-ward AQI table */}
              <section>
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                  Per-Ward Avg AQI — Last {days} Days
                </h2>
                <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
                  <WardTable rows={summary.ward_aqi_table} />
                </div>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
