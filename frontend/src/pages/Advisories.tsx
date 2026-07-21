import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import { fetchAdvisories, fetchIvrAdvisory, generateAdvisories, sendAdvisoryWhatsApp } from "@/features/advisory/api";
import type { WhatsAppDeliveryResult } from "@/features/advisory/api";
import type { Advisory } from "@/lib/types";

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

function DeliveryBadge({ label, sent, icon }: { label: string; sent: boolean; icon: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${
        sent
          ? "bg-green-500/10 text-green-400 border-green-500/30"
          : "bg-slate-800 text-slate-500 border-slate-700"
      }`}
    >
      {icon} {label} {sent && "✓"}
    </span>
  );
}

function AdvisoryCard({
  advisory,
  cityId,
  canSend,
}: {
  advisory: Advisory;
  cityId: string;
  canSend: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [sending, setSending] = useState(false);
  const [deliveryResult, setDeliveryResult] = useState<WhatsAppDeliveryResult | null>(null);

  const langLabel = LANGUAGE_LABELS[advisory.language] ?? advisory.language.toUpperCase();
  const dateStr = new Date(advisory.created_at).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const isWhatsappSent = advisory.channel === "whatsapp" || deliveryResult?.status === "sent" || deliveryResult?.status === "mock";
  const sentTime = deliveryResult?.sent_at
    ? new Date(deliveryResult.sent_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
    : advisory.sent_at
    ? new Date(advisory.sent_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
    : null;

  async function handleSendWhatsApp() {
    setSending(true);
    try {
      const result = await sendAdvisoryWhatsApp(cityId, advisory.id);
      setDeliveryResult(result);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white leading-snug mb-1">{advisory.title}</h3>
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
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">Primary source:</span>
          <span className="text-xs font-medium text-blue-400 capitalize">{advisory.dominant_source}</span>
        </div>
      )}

      <p className={`text-sm text-slate-300 leading-relaxed ${!expanded ? "line-clamp-3" : ""}`}>
        {advisory.body}
      </p>
      {advisory.body.length > 200 && (
        <button
          className="text-xs text-blue-400 hover:text-blue-300 transition-colors self-start"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : "Read more"}
        </button>
      )}

      {/* Delivery channels */}
      <div className="pt-3 border-t border-slate-800 space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <DeliveryBadge label="Web" sent icon="🌐" />
          <DeliveryBadge label="IVR" sent icon="📞" />
          <DeliveryBadge label="WhatsApp" sent={isWhatsappSent} icon="💬" />
        </div>

        {/* WhatsApp delivery log */}
        {deliveryResult && (
          <div
            className={`rounded-lg px-3 py-2 text-xs font-mono border ${
              deliveryResult.status === "error"
                ? "bg-red-500/10 border-red-500/30 text-red-400"
                : "bg-green-500/10 border-green-500/30 text-green-300"
            }`}
          >
            {deliveryResult.status === "error" ? (
              <span>✗ Failed: {deliveryResult.error}</span>
            ) : (
              <span>
                {deliveryResult.mock ? "🔵 Mock delivery" : "✓ Sent"} → {deliveryResult.phone} at{" "}
                {sentTime} · SID: {deliveryResult.sid}
                {deliveryResult.mock && (
                  <span className="text-slate-500"> (set TWILIO_ENABLED=true for live)</span>
                )}
              </span>
            )}
          </div>
        )}

        {/* Send button */}
        {canSend && !isWhatsappSent && (
          <button
            onClick={handleSendWhatsApp}
            disabled={sending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 border border-green-500/30 text-green-400 hover:text-green-300 text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {sending ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-green-400 border-t-transparent animate-spin" />
                Sending…
              </>
            ) : (
              <>💬 Send WhatsApp</>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default function Advisories() {
  const { user } = useAuth();
  const { selectedCityId } = useCities();
  const queryClient = useQueryClient();

  const [langFilter, setLangFilter] = useState<string>("");
  const [ivrLang, setIvrLang] = useState<string>("en");
  const [showIvr, setShowIvr] = useState(false);

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

  const { data: ivrData, isLoading: ivrLoading } = useQuery({
    queryKey: ["ivr-advisory", selectedCityId, ivrLang],
    queryFn: () => fetchIvrAdvisory(selectedCityId!, ivrLang),
    enabled: !!selectedCityId && showIvr,
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

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-950 text-white">
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

            <button
              onClick={() => setShowIvr((v) => !v)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${showIvr ? "bg-green-600/20 border-green-500/40 text-green-300" : "bg-slate-800 border-slate-700 text-slate-400 hover:text-white hover:border-slate-500"}`}
            >
              📞 IVR Preview
            </button>

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

        {/* IVR Preview Panel */}
        {showIvr && (
          <div className="bg-slate-800 border-b border-slate-700 px-6 py-4">
            <div className="max-w-2xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">📞</span>
                  <span className="text-sm font-semibold text-white">IVR Preview</span>
                  <span className="text-xs text-slate-500">Text-to-speech script for phone alerts</span>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={ivrLang}
                    onChange={(e) => setIvrLang(e.target.value)}
                    className="bg-slate-700 border border-slate-600 text-slate-300 text-xs rounded px-2 py-1"
                  >
                    {Object.entries(LANGUAGE_LABELS).filter(([k]) => ["en","hi","kn","ta"].includes(k)).map(([code, label]) => (
                      <option key={code} value={code}>{label}</option>
                    ))}
                  </select>
                  <button onClick={() => setShowIvr(false)} className="text-slate-500 hover:text-slate-300 text-xs">✕ Close</button>
                </div>
              </div>
              <div className="bg-slate-900 rounded-lg border border-slate-700 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-xs text-slate-500 font-mono">CALL IN PROGRESS — {LANGUAGE_LABELS[ivrLang] ?? ivrLang.toUpperCase()}</span>
                </div>
                {ivrLoading ? (
                  <p className="text-slate-500 text-sm italic">Loading IVR script…</p>
                ) : ivrData ? (
                  <p className="text-slate-200 text-sm leading-relaxed font-mono">{ivrData.ivr_text}</p>
                ) : (
                  <p className="text-slate-500 text-sm italic">No advisory available — generate one first.</p>
                )}
                {ivrData?.aqi_level && (
                  <div className="mt-2 pt-2 border-t border-slate-800 text-xs text-slate-600">
                    AQI level: {ivrData.aqi_level} · Advisory ID: {ivrData.advisory_id?.slice(0, 8)}…
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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
                <AdvisoryCard key={adv.id} advisory={adv} cityId={selectedCityId!} canSend={canGenerate} />
              ))}
            </div>
          )}
        </main>
    </div>
  );
}
