import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import {
  fetchEnforcementQueue,
  rankEnforcementQueue,
  updateEnforcementStatus,
  type EnforcementItem,
} from "@/features/enforcement/api";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/enforcement", label: "Enforcement", icon: "🚨" },
  { to: "/advisories", label: "Advisories", icon: "📢" },
  { to: "/admin/cities", label: "City Admin", icon: "🏙️" },
];

function permitBadge(status: string) {
  const styles: Record<string, string> = {
    active: "bg-green-500/20 text-green-400 border-green-500/30",
    pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    expired: "bg-red-500/20 text-red-400 border-red-500/30",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-semibold border uppercase tracking-wide ${
        styles[status] ?? "bg-slate-700 text-slate-300 border-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

function sourceTypeBadge(type: string) {
  const colors: Record<string, string> = {
    vehicular: "text-blue-400",
    industrial: "text-purple-400",
    construction: "text-yellow-400",
    agricultural: "text-lime-400",
    fire: "text-orange-400",
  };
  return <span className={`text-xs font-medium ${colors[type] ?? "text-slate-400"}`}>{type}</span>;
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? "bg-red-500" : pct >= 45 ? "bg-orange-400" : pct >= 25 ? "bg-yellow-400" : "bg-green-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-400 w-8 text-right">{score.toFixed(2)}</span>
    </div>
  );
}

export default function Enforcement() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { selectedCityId } = useCities();
  const qc = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const cityId = selectedCityId ?? "";

  const { data, isLoading, error } = useQuery({
    queryKey: ["enforcement", cityId, statusFilter],
    queryFn: () => fetchEnforcementQueue(cityId, statusFilter || undefined),
    enabled: !!cityId,
  });

  const rankMutation = useMutation({
    mutationFn: () => rankEnforcementQueue(cityId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enforcement", cityId] }),
  });

  const dispatchMutation = useMutation({
    mutationFn: (itemId: string) => updateEnforcementStatus(cityId, itemId, "dispatched"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enforcement", cityId] }),
  });

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

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
            <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400 uppercase tracking-wide font-semibold">
              {user?.role}
            </span>
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
          <h1 className="text-lg font-semibold text-white">Enforcement Queue</h1>
          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="dispatched">Dispatched</option>
              <option value="completed">Completed</option>
            </select>
            <button
              onClick={() => rankMutation.mutate()}
              disabled={rankMutation.isPending || !cityId}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
            >
              {rankMutation.isPending ? "Re-ranking…" : "Re-rank"}
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {!cityId ? (
            <div className="text-slate-500 text-center mt-16">No city selected.</div>
          ) : isLoading ? (
            <div className="text-slate-500 text-center mt-16">Loading enforcement queue…</div>
          ) : error ? (
            <div className="text-red-400 text-center mt-16">Failed to load enforcement queue.</div>
          ) : (
            <>
              <div className="mb-4 flex items-center gap-2 text-sm text-slate-400">
                <span>{data?.total ?? 0} sources in queue</span>
              </div>
              <div className="space-y-2">
                {data?.items.map((item: EnforcementItem, idx: number) => (
                  <div
                    key={item.id}
                    className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden"
                  >
                    <div
                      className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
                      onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    >
                      {/* Rank */}
                      <span className="w-6 text-xs text-slate-600 font-mono text-center">
                        #{idx + 1}
                      </span>

                      {/* Source info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium text-white truncate">
                            {item.source?.name ?? item.emission_source_id}
                          </span>
                          {item.source && sourceTypeBadge(item.source.type)}
                          {item.source && permitBadge(item.source.permit_status)}
                        </div>
                        <ScoreBar score={item.priority_score} />
                      </div>

                      {/* Status */}
                      <div className="flex items-center gap-3 shrink-0">
                        <span
                          className={`text-xs px-2 py-0.5 rounded border font-medium ${
                            item.status === "pending"
                              ? "text-orange-400 border-orange-500/30 bg-orange-500/10"
                              : item.status === "dispatched"
                              ? "text-blue-400 border-blue-500/30 bg-blue-500/10"
                              : "text-green-400 border-green-500/30 bg-green-500/10"
                          }`}
                        >
                          {item.status}
                        </span>
                        {item.status === "pending" && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              dispatchMutation.mutate(item.id);
                            }}
                            disabled={dispatchMutation.isPending}
                            className="px-3 py-1 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 rounded-lg text-xs font-medium transition-colors"
                          >
                            Dispatch
                          </button>
                        )}
                        <span className="text-slate-600 text-xs">{expandedId === item.id ? "▲" : "▼"}</span>
                      </div>
                    </div>

                    {/* Expanded evidence brief */}
                    {expandedId === item.id && item.evidence_brief_text && (
                      <div className="px-5 pb-4 border-t border-slate-800/60">
                        <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mt-3 mb-2">
                          Evidence Brief
                        </p>
                        <p className="text-sm text-slate-300 leading-relaxed">
                          {item.evidence_brief_text}
                        </p>
                        {item.source?.last_inspected_at && (
                          <p className="text-xs text-slate-500 mt-2">
                            Last inspected:{" "}
                            {new Date(item.source.last_inspected_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
