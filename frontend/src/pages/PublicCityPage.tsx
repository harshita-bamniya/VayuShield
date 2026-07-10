import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import client from "@/lib/apiClient";

interface PublicSummary {
  city: { id: string; name: string; state: string };
  aqi: number | null;
  aqi_level: string;
  dominant_source: string | null;
  pollutants: { pm25: number | null; pm10: number | null; no2: number | null };
  last_updated: string | null;
  advisories: { en?: { title: string; body: string }; hi?: { title: string; body: string } };
  all_cities: { id: string; name: string; state: string }[];
}

async function fetchPublicSummary(cityId: string): Promise<PublicSummary> {
  const resp = await client.get<{ data: PublicSummary }>(`/cities/${cityId}/public/summary`);
  return resp.data.data!;
}

function aqiBg(level: string): string {
  switch (level) {
    case "Good": return "bg-green-500";
    case "Satisfactory": return "bg-lime-500";
    case "Moderate": return "bg-yellow-500";
    case "Poor": return "bg-orange-500";
    case "Very Poor": return "bg-red-500";
    case "Severe": return "bg-purple-600";
    default: return "bg-gray-500";
  }
}

function aqiText(level: string): string {
  switch (level) {
    case "Good": return "text-green-400";
    case "Satisfactory": return "text-lime-400";
    case "Moderate": return "text-yellow-400";
    case "Poor": return "text-orange-400";
    case "Very Poor": return "text-red-400";
    case "Severe": return "text-purple-400";
    default: return "text-gray-400";
  }
}

function HealthCard({ icon, title, subtitle, show }: { icon: string; title: string; subtitle: string; show: boolean }) {
  if (!show) return null;
  return (
    <div className="flex items-start gap-3 bg-gray-800 border border-gray-700 rounded-xl p-4">
      <span className="text-2xl">{icon}</span>
      <div>
        <p className="font-semibold text-white">{title}</p>
        <p className="text-sm text-gray-400">{subtitle}</p>
      </div>
    </div>
  );
}

function fmt(v: number | null): string {
  return v != null ? v.toString() : "—";
}

export default function PublicCityPage() {
  const { cityId } = useParams<{ cityId: string }>();
  const navigate = useNavigate();
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [copied, setCopied] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["public-summary", cityId],
    queryFn: () => fetchPublicSummary(cityId!),
    refetchInterval: 5 * 60 * 1000,
    enabled: !!cityId,
  });

  function handleCopy() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleCityChange(e: React.ChangeEvent<HTMLSelectElement>) {
    navigate(`/city/${e.target.value}/public`);
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400">
        Loading air quality data…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-red-400">
        City not found or data unavailable.
      </div>
    );
  }

  const { city, aqi, aqi_level, dominant_source, pollutants, last_updated, advisories, all_cities } = data;
  const advisory = advisories[lang];
  const isHighAqi = ["Poor", "Very Poor", "Severe"].includes(aqi_level);
  const isModerate = aqi_level === "Moderate" || isHighAqi;

  const lastUpdatedStr = last_updated
    ? new Date(last_updated).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour12: true })
    : "No recent data";

  const sourceLabel: Record<string, string> = {
    vehicular: "Vehicular Emissions",
    industrial: "Industrial Activities",
    construction: "Construction Dust",
    agricultural: "Agricultural Burning",
    fire: "Active Fire Hotspots",
    other: "Mixed Sources",
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🛡️</span>
          <span className="font-bold text-lg tracking-tight">VayuShield AI</span>
          <span className="text-gray-500 text-sm ml-1">Public Advisory</span>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={cityId}
            onChange={handleCityChange}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none"
          >
            {all_cities.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}, {c.state}
              </option>
            ))}
          </select>
          <button
            onClick={handleCopy}
            className="text-sm bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 hover:bg-gray-700 transition-colors"
          >
            {copied ? "✅ Copied!" : "🔗 Share"}
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* AQI Banner */}
        <div className={`rounded-2xl p-6 text-center ${aqiBg(aqi_level)} bg-opacity-20 border border-opacity-30 border-current`}>
          <p className="text-sm text-gray-300 mb-1 uppercase tracking-widest font-medium">
            {city.name}, {city.state}
          </p>
          <div className={`text-8xl font-black ${aqiText(aqi_level)} my-3`}>
            {aqi ?? "—"}
          </div>
          <div className={`text-2xl font-bold ${aqiText(aqi_level)}`}>{aqi_level}</div>
          <p className="text-gray-400 text-sm mt-3">AQI (CPCB Scale) · Updated {lastUpdatedStr}</p>
          {dominant_source && (
            <p className="text-gray-300 text-sm mt-1">
              Primary source: <span className="font-medium">{sourceLabel[dominant_source] ?? dominant_source}</span>
            </p>
          )}
        </div>

        {/* Pollutant Row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "PM2.5", value: pollutants.pm25 },
            { label: "PM10", value: pollutants.pm10 },
            { label: "NO₂", value: pollutants.no2 },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
              <p className="text-xl font-bold text-white">{fmt(value)}</p>
              <p className="text-xs text-gray-600 mt-0.5">µg/m³</p>
            </div>
          ))}
        </div>

        {/* Advisory Section */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-lg">Health Advisory</h2>
            <div className="flex bg-gray-800 rounded-lg p-0.5">
              <button
                onClick={() => setLang("en")}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${lang === "en" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}
              >
                EN
              </button>
              <button
                onClick={() => setLang("hi")}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${lang === "hi" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}
              >
                हिं
              </button>
            </div>
          </div>

          {advisory ? (
            <div>
              <p className="font-semibold text-white mb-2">{advisory.title}</p>
              <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-line">{advisory.body}</p>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">
              No advisory available in {lang === "en" ? "English" : "Hindi"} yet.
              {lang === "hi" && advisories.en && (
                <button onClick={() => setLang("en")} className="ml-2 text-blue-400 underline">
                  Show English
                </button>
              )}
            </p>
          )}
        </div>

        {/* Health Recommendations */}
        {isModerate && (
          <div className="space-y-3">
            <h2 className="font-bold text-lg">Recommended Actions</h2>
            <HealthCard
              icon="🏠"
              title="Stay Indoors"
              subtitle="Limit outdoor activity, especially for children and the elderly."
              show={isHighAqi}
            />
            <HealthCard
              icon="😷"
              title="Wear N95 Mask"
              subtitle="Use an N95 or P100 respirator if going outside is unavoidable."
              show={isHighAqi}
            />
            <HealthCard
              icon="🚫"
              title="Avoid Outdoor Exercise"
              subtitle="Postpone jogging, cycling, or other strenuous outdoor activities."
              show={isModerate}
            />
          </div>
        )}

        {/* Footer */}
        <p className="text-center text-gray-600 text-xs pb-4">
          Data from CPCB / NASA FIRMS · VayuShield AI · ET AI Hackathon 2026
        </p>
      </main>
    </div>
  );
}
