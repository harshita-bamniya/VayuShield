import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import type { Layer, PathOptions } from "leaflet";
import type { WardWithAqi } from "@/lib/types";

interface WardMapProps {
  wards: WardWithAqi[];
  onWardClick?: (wardId: string) => void;
}

function aqiFillColor(aqi: number | null): string {
  if (aqi === null || aqi === undefined) return "#94a3b8";
  if (aqi <= 50) return "#22c55e";
  if (aqi <= 100) return "#a3e635";
  if (aqi <= 200) return "#eab308";
  if (aqi <= 300) return "#f97316";
  if (aqi <= 400) return "#ef4444";
  return "#a855f7";
}

function wardStyle(ward: WardWithAqi): PathOptions {
  return {
    fillColor: aqiFillColor(ward.avg_aqi),
    fillOpacity: 0.55,
    color: "#1e293b",
    weight: 1.5,
  };
}

export default function WardMap({ wards, onWardClick }: WardMapProps) {
  const wardsWithGeom = wards.filter((w) => w.geometry);

  return (
    <MapContainer
      center={[28.62, 77.21]}
      zoom={10}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {wardsWithGeom.map((ward) => (
        <GeoJSON
          key={ward.id}
          data={{ type: "Feature", properties: ward, geometry: ward.geometry } as never}
          style={() => wardStyle(ward)}
          onEachFeature={(_feat: unknown, layer: Layer) => {
            const label = `<strong>${ward.name}</strong><br/>AQI: ${
              ward.avg_aqi !== null ? ward.avg_aqi : "No data"
            }${ward.aqi_category ? ` (${ward.aqi_category})` : ""}`;
            (layer as { bindTooltip: (s: string) => void }).bindTooltip(label);
            if (onWardClick) {
              layer.on("click", () => onWardClick(ward.id));
            }
          }}
        />
      ))}
    </MapContainer>
  );
}
