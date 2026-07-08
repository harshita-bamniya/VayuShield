import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { ForecastPoint } from "./api";

interface Props {
  points: ForecastPoint[];
  generatedAt: string;
  peakAqi: number;
}

const AQI_BANDS = [
  { label: "Good", max: 50, color: "#22c55e" },
  { label: "Satisfactory", max: 100, color: "#84cc16" },
  { label: "Moderate", max: 200, color: "#eab308" },
  { label: "Poor", max: 300, color: "#f97316" },
  { label: "Very Poor", max: 400, color: "#ef4444" },
  { label: "Severe", max: 500, color: "#7c3aed" },
];

function aqiColor(aqi: number): string {
  for (const band of AQI_BANDS) {
    if (aqi <= band.max) return band.color;
  }
  return "#7c3aed";
}

function formatHour(iso: string): string {
  const d = new Date(iso);
  const h = d.getHours();
  if (h === 0) return `${d.getDate()}/${d.getMonth() + 1}`;
  return `${String(h).padStart(2, "0")}:00`;
}

// Custom dot: color by AQI band
function CustomDot(props: {
  cx?: number;
  cy?: number;
  payload?: ForecastPoint;
}) {
  const { cx, cy, payload } = props;
  if (!payload || cx == null || cy == null) return null;
  return <circle cx={cx} cy={cy} r={2} fill={aqiColor(payload.predicted_aqi)} />;
}

export default function ForecastChart({ points, generatedAt, peakAqi }: Props) {
  const chartData = useMemo(
    () =>
      points.map((p) => ({
        ...p,
        label: formatHour(p.forecast_for_ts),
      })),
    [points]
  );

  const freshAt = new Date(generatedAt).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-white">72-Hour AQI Forecast</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Generated at {freshAt} · model: diurnal-v1
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Peak:</span>
          <span
            className="px-2 py-0.5 rounded-md text-xs font-bold"
            style={{ backgroundColor: aqiColor(peakAqi) + "33", color: aqiColor(peakAqi) }}
          >
            AQI {peakAqi}
          </span>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "#64748b" }}
            interval={5}
            tickLine={false}
          />
          <YAxis
            domain={[0, 500]}
            tick={{ fontSize: 10, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #1e293b",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(value: number) => [
              `${value} AQI`,
              "Predicted",
            ]}
          />
          {/* AQI threshold lines */}
          <ReferenceLine y={200} stroke="#f97316" strokeDasharray="4 4" strokeOpacity={0.5} />
          <ReferenceLine y={300} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.5} />
          <ReferenceLine y={400} stroke="#7c3aed" strokeDasharray="4 4" strokeOpacity={0.5} />
          <Line
            type="monotone"
            dataKey="predicted_aqi"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={{ r: 5, fill: "#3b82f6" }}
            name="AQI Forecast"
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend for thresholds */}
      <div className="flex gap-4 mt-3 flex-wrap">
        {AQI_BANDS.map((b) => (
          <div key={b.label} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ backgroundColor: b.color }}
            />
            <span className="text-xs text-slate-500">{b.label} (≤{b.max})</span>
          </div>
        ))}
      </div>
    </div>
  );
}
