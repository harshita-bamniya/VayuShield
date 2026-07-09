import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import { fetchAdvisories, generateAdvisories } from "@/features/advisory/api";
import type { Advisory } from "@/lib/types";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/enforcement", label: "Enforcement", icon: "🚨" },
  { to: "/advisories", label: "Advisories", icon: "📢" },
  { to: "/reports", label: "Reports", icon: "📄" },
  { to: "/admin/cities", label: "City Admin", icon: "🏙️" },
];

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  hi: "हिंदी",
  mr: "मराठी",
  kn: "ಕನ್ನಡ",
  ta: "தமிழ்",
  bn: "বাংলা",
  gu: "ગુજરાતી",
};

const AQI_LEVEL_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Good: { bg: "bg-green-500/10", text: "text-green-400", border: "border-green-500/30" },
  Satisfactory: { bg: "bg-lime-500/10", text: "text-lime-400", border: "border-lime-500/30" },
  Moderate: { bg: "bg-yellow-500/10", text: "text-yellow-400", border: "border-yellow-500/30" },
  Poor: { bg: "bg-orange-500/10", text: "text-orange-400", border: "border-orange-500/30" },
  "Very Poor": { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/30" },
  Severe: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30" },
};

function AqiBadge({ level }: { level: string }) {
  const style = AQI_LEVEL_COLORS[level] ?? AQI_LEVEL_COLORS["Moderate"];
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold border ${style.bg} ${style.text} ${style.border}`}
    >
      {level}
    </span>
  );
}

function AdvisoryCard({ advisory }: { advisory: Advisory }) {
  const [expanded, setExpanded] = useState(false);
  const langLabel = LANGUAGE_LABELS[advisory.language] ?? advisory.language.toUpperCase();
  const dateStr = new Date(advisory.created_at).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white leading-snug mb-1">
            {advisory.title}
          </h3>
          <p className="text-xs text-slate-500">{dateStr}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <AqiBadge level={advisory.aqi_level} />
          <span className="inline-block px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-400 border border-slate-700">
            {langLabel}
          </span>
        </div>
      </div>

      {advisory.dominant_source && (
        <div className="flex items-center gap-1.5 mb-3">
          <span className="text-xs text-slate-500">Primary source:</span>
          <span className="text-xs font-medium text-blue-400 capitalize">
            {advisory.dominant_source}
          </span>
        </div>
      )}

      <p className={`text-sm text-slate-300 leading-relaxed ${!expanded ? "line-clamp-3" : ""}`}>
        {advisory.body}
      </p>
      {advisory.body.length > 200 && (
        <button
          className="mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : "Read more"}
        </button>
      )}

      <div className="mt-3 pt-3 border-t border-slate-800 flex items-center gap-2">
        <span className="text-xs text-slate-600 capitalize">{advisory.channel}</span>
        {advisory.sent_at && (
          <span className="text-xs text-green-500">✓ Sent</span>
        )}
      </div>
    </div>
  );
}

export default function Advisories() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { selectedCityId } = useCities();
  const queryClient = useQueryClient();

  const [langFilter, setLangFilter] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["advisories", selectedCityId, langFilter],
    queryFn: () =>
      fetchAdvisories(selectedCityId!, {
        language: langFilter || undefined,
        limit: 50,
      }),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateAdvisories(selectedCityId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["advisories"] });
      queryClient.invalidateQueries({ queryKey: ["advisory-count"] });
    },
  });

  const canGenerate = user?.role === "admin" || user?.role === "sysadmin";

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="flex h-screen bg-slate-950 text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-400/40 flex items-center justify-center text-sm">
              🌬️
            </div>
            <span className="font-bold text-white tracking-tight">VayuShield AI</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-500/20 text-blue-300"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-800">
          <div className="px-3 py-2 mb-1">
            <p className="text-xs text-slate-500">Signed in as</p>
            <p className="text-sm text-slate-300 truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 shrink-0">
          <h1 className="text-lg font-semibold text-white">Public Advisories</h1>
          <div className="flex items-center gap-3">
            {/* Language filter */}
            <select
              value={langFilter}
              onChange={(e) => setLangFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All languages</option>
              {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>

            {canGenerate && (
              <button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending || !selectedCityId}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {generateMutation.isPending ? "Generating…" : "Generate Advisories"}
              </button>
            )}
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {generateMutation.isSuccess && (
            <div className="mb-4 px-4 py-3 bg-green-500/10 border border-green-500/30 rounded-lg text-sm text-green-400">
              Generated {generateMutation.data?.generated} new{" "}
              {generateMutation.data?.generated === 1 ? "advisory" : "advisories"}
              {generateMutation.data?.skipped
                ? `, ${generateMutation.data.skipped} already up-to-date`
                : ""}
              .
            </div>
          )}

          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-400">
              {total} {total === 1 ? "advisory" : "advisories"}
              {langFilter ? ` in ${LANGUAGE_LABELS[langFilter] ?? langFilter}` : ""}
            </p>
          </div>

          {!selectedCityId ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-slate-600 text-sm">No city selected</p>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-slate-600 text-sm">Loading advisories…</p>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <p className="text-4xl">📢</p>
              <p className="text-slate-500 text-sm">No advisories yet.</p>
              {canGenerate && (
                <button
                  onClick={() => generateMutation.mutate()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Generate first advisory
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {items.map((adv) => (
                <AdvisoryCard key={adv.id} advisory={adv} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
