import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import {
  fetchEnforcementQueue,
  rankEnforcementQueue,
  regenerateAiBrief,
  updateEnforcementStatus,
  type EnforcementItem,
} from "@/features/enforcement/api";

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
  const { user } = useAuth();
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

  const aiBriefMutation = useMutation({
    mutationFn: (itemId: string) => regenerateAiBrief(cityId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enforcement", cityId] }),
  });

  const canUseAi = user?.role === "admin" || user?.role === "sysadmin";

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-950 text-white">
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
              {/* Intervention effectiveness summary banner */}
              {data && data.items.length > 0 && (() => {
                const items = data.items;
                const completed = items.filter((i: EnforcementItem) => i.status === "completed").length;
                const dispatched = items.filter((i: EnforcementItem) => i.status === "dispatched").length;
                const pending = items.filter((i: EnforcementItem) => i.status === "pending").length;
                const total = items.length;
                const completionRate = Math.round((completed / total) * 100);
                return (
                  <div className="mb-4 bg-slate-900 border border-slate-800 rounded-xl p-4 grid grid-cols-4 gap-4">
                    <div className="text-center">
                      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Pending</p>
                      <p className="text-xl font-bold text-orange-400">{pending}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Dispatched</p>
                      <p className="text-xl font-bold text-sky-400">{dispatched}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Completed</p>
                      <p className="text-xl font-bold text-green-400">{completed}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Completion Rate</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-green-500 transition-all"
                            style={{ width: `${completionRate}%` }}
                          />
                        </div>
                        <span className="text-sm font-mono font-bold text-green-400 shrink-0">{completionRate}%</span>
                      </div>
                    </div>
                  </div>
                );
              })()}
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
                    {expandedId === item.id && (
                      <div className="px-5 pb-4 border-t border-slate-800/60">
                        <div className="flex items-center justify-between mt-3 mb-2">
                          <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">
                            Evidence Brief
                          </p>
                          {canUseAi && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                aiBriefMutation.mutate(item.id);
                              }}
                              disabled={aiBriefMutation.isPending}
                              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg bg-violet-600/20 hover:bg-violet-600/40 text-violet-300 border border-violet-500/30 disabled:opacity-50 transition-colors"
                            >
                              {aiBriefMutation.isPending && aiBriefMutation.variables === item.id
                                ? "Generating…"
                                : "✨ AI Brief"}
                            </button>
                          )}
                        </div>
                        {item.evidence_brief_text ? (
                          <p className="text-sm text-slate-300 leading-relaxed">
                            {item.evidence_brief_text}
                          </p>
                        ) : (
                          <p className="text-sm text-slate-500 italic">No brief generated yet.</p>
                        )}
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
  );
}
