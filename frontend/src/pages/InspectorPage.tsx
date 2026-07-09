/**
 * Module 10 — Inspector PWA
 * Mobile-optimised view for field inspectors.
 * No sidebar — uses a sticky top header bar instead.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import {
  fetchEnforcementQueue,
  logInspection,
  updateEnforcementStatus,
  type EnforcementItem,
} from "@/features/enforcement/api";

const OUTCOMES = [
  { value: "passed", label: "✅ Passed", color: "text-green-400" },
  { value: "warning", label: "⚠️ Warning", color: "text-yellow-400" },
  { value: "failed", label: "❌ Failed", color: "text-red-400" },
];

function permitBadge(status: string) {
  const styles: Record<string, string> = {
    active: "bg-green-900/40 text-green-300 border-green-700",
    pending: "bg-yellow-900/40 text-yellow-300 border-yellow-700",
    expired: "bg-red-900/40 text-red-300 border-red-700",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold border uppercase tracking-wide ${
        styles[status] ?? "bg-slate-700 text-slate-300 border-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

function priorityColor(score: number) {
  if (score >= 0.7) return "text-red-400";
  if (score >= 0.45) return "text-orange-400";
  if (score >= 0.25) return "text-yellow-400";
  return "text-green-400";
}

interface InspectionFormProps {
  item: EnforcementItem;
  cityId: string;
  onDone: () => void;
  onCancel: () => void;
}

function InspectionForm({ item, cityId, onDone, onCancel }: InspectionFormProps) {
  const [outcome, setOutcome] = useState("passed");
  const [notes, setNotes] = useState("");
  const queryClient = useQueryClient();

  const submitMutation = useMutation({
    mutationFn: async () => {
      await logInspection(cityId, item.id, {
        outcome,
        notes: notes.trim() || undefined,
        completed_at: new Date().toISOString(),
      });
      await updateEnforcementStatus(cityId, item.id, "completed");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inspector-queue", cityId] });
      onDone();
    },
  });

  return (
    <div className="mt-4 rounded-xl border border-slate-600 bg-slate-800/60 p-4 space-y-4">
      <p className="text-sm font-semibold text-slate-300">Inspection Report</p>

      {/* Outcome selector — large touch targets */}
      <div className="grid grid-cols-3 gap-2">
        {OUTCOMES.map((o) => (
          <button
            key={o.value}
            onClick={() => setOutcome(o.value)}
            className={`py-3 rounded-xl text-sm font-semibold border transition-all ${
              outcome === o.value
                ? "border-blue-500 bg-blue-600/30 text-white"
                : "border-slate-600 bg-slate-700/40 text-slate-400 active:bg-slate-700"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Notes field */}
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Inspection notes (optional)…"
        rows={3}
        className="w-full rounded-xl bg-slate-900 border border-slate-600 text-slate-200 text-sm p-3 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {submitMutation.isError && (
        <p className="text-red-400 text-xs">Submission failed — try again.</p>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => submitMutation.mutate()}
          disabled={submitMutation.isPending}
          className="flex-1 py-3.5 rounded-xl bg-blue-600 text-white font-semibold text-sm active:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {submitMutation.isPending ? "Submitting…" : "Submit Inspection"}
        </button>
        <button
          onClick={onCancel}
          disabled={submitMutation.isPending}
          className="px-5 py-3.5 rounded-xl bg-slate-700 text-slate-300 font-semibold text-sm active:bg-slate-600 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

interface QueueCardProps {
  item: EnforcementItem;
  cityId: string;
}

function QueueCard({ item, cityId }: QueueCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [done, setDone] = useState(false);

  const src = item.source;

  if (done) {
    return (
      <div className="rounded-2xl border border-green-700/50 bg-green-900/20 p-4 text-center">
        <p className="text-green-400 font-semibold">✅ Inspection Submitted</p>
        <p className="text-slate-400 text-xs mt-1">{src?.name ?? item.emission_source_id}</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800/70 overflow-hidden">
      {/* Card header — always visible */}
      <div className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-semibold text-white text-base leading-tight truncate">
              {src?.name ?? "Unknown Source"}
            </p>
            <p className="text-slate-400 text-xs mt-0.5 capitalize">
              {src?.type ?? "—"} · {item.status}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className={`text-xl font-bold font-mono ${priorityColor(item.priority_score)}`}>
              {(item.priority_score * 100).toFixed(0)}
            </p>
            <p className="text-slate-500 text-[10px]">priority</p>
          </div>
        </div>

        {/* Permit badge */}
        {src && (
          <div className="flex items-center gap-2">
            {permitBadge(src.permit_status)}
            {src.last_inspected_at && (
              <span className="text-slate-500 text-xs">
                Last: {new Date(src.last_inspected_at).toLocaleDateString()}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Evidence brief — expandable */}
      {item.evidence_brief_text && (
        <div className="px-4 pb-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-blue-400 underline-offset-2 underline"
          >
            {expanded ? "Hide brief" : "Show evidence brief"}
          </button>
          {expanded && (
            <p className="text-slate-300 text-sm mt-2 leading-relaxed">
              {item.evidence_brief_text}
            </p>
          )}
        </div>
      )}

      {/* Inspection form or Start button */}
      <div className="px-4 pb-4">
        {inspecting ? (
          <InspectionForm
            item={item}
            cityId={cityId}
            onDone={() => { setInspecting(false); setDone(true); }}
            onCancel={() => setInspecting(false)}
          />
        ) : (
          <button
            onClick={() => setInspecting(true)}
            className="w-full py-3.5 rounded-xl bg-slate-700 hover:bg-slate-600 active:bg-slate-500 text-white font-semibold text-sm transition-colors"
          >
            Start Inspection
          </button>
        )}
      </div>
    </div>
  );
}

export default function InspectorPage() {
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const cityId = useCities((s) => s.selectedCityId) ?? user?.city_id ?? "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["inspector-queue", cityId],
    queryFn: () => fetchEnforcementQueue(cityId, undefined),
    enabled: !!cityId,
  });

  // Show pending + dispatched items for inspectors
  const activeItems = (data?.items ?? []).filter(
    (item) => item.status === "pending" || item.status === "dispatched",
  );

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Sticky top header — no sidebar */}
      <header className="sticky top-0 z-20 bg-slate-900/95 backdrop-blur border-b border-slate-700/60 px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-widest font-semibold">VayuShield</p>
          <h1 className="text-base font-bold text-white leading-tight">Inspector Queue</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 hidden sm:block">{user?.full_name ?? user?.email}</span>
          <button
            onClick={logout}
            className="text-xs text-slate-400 border border-slate-600 px-3 py-1.5 rounded-lg active:bg-slate-700"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Queue summary pill */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 bg-orange-900/30 border border-orange-700/50 text-orange-300 text-xs font-semibold px-3 py-1.5 rounded-full">
            🔴 {activeItems.length} pending
          </span>
          <button
            onClick={() => refetch()}
            className="text-xs text-slate-400 underline underline-offset-2"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 px-4 py-2 pb-8 space-y-3 max-w-lg mx-auto w-full">
        {isLoading && (
          <div className="text-center py-16 text-slate-500">Loading queue…</div>
        )}

        {isError && (
          <div className="rounded-xl border border-red-700/50 bg-red-900/20 p-4 text-center">
            <p className="text-red-400 font-semibold">Failed to load queue</p>
            <button onClick={() => refetch()} className="text-xs text-slate-400 mt-2 underline">
              Retry
            </button>
          </div>
        )}

        {!isLoading && !isError && activeItems.length === 0 && (
          <div className="text-center py-16">
            <p className="text-4xl mb-3">🎉</p>
            <p className="text-slate-400 font-medium">All clear — no pending items.</p>
          </div>
        )}

        {activeItems.map((item) => (
          <QueueCard key={item.id} item={item} cityId={cityId} />
        ))}
      </main>
    </div>
  );
}
