import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, TileLayer, WMSTileLayer, GeoJSON, CircleMarker, Popup, useMap } from "react-leaflet";
import type { Layer, PathOptions } from "leaflet";
import type { WardWithAqi } from "@/lib/types";
import type { FireHotspot, TrafficSegment } from "@/features/cities/api";

// NASA GIBS WMS — MODIS Terra Aerosol Optical Depth (daily, no auth required)
const GIBS_WMS_URL = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi";

function MapRecenter({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 10, { duration: 0.8 });
  }, [center[0], center[1]]);
  return null;
}

function trafficColor(ratio: number): string {
  if (ratio < 1.0) return "#22c55e";   // clear — green
  if (ratio < 1.5) return "#a3e635";   // normal — lime
  if (ratio < 2.5) return "#f97316";   // moderate — orange
  return "#ef4444";                     // heavy — red
}

interface WardMapProps {
  wards: WardWithAqi[];
  onWardClick?: (wardId: string) => void;
  fireHotspots?: FireHotspot[];
  trafficSegments?: TrafficSegment[];
  center?: [number, number];
  showSatellite?: boolean;
  showTraffic?: boolean;
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

function hotspotColor(confidence: number): string {
  return confidence >= 75 ? "#ef4444" : "#f97316";
}

function hotspotRadius(frp: number | null): number {
  return frp ? Math.max(6, Math.min(20, frp / 10)) : 8;
}

export default function WardMap({ wards, onWardClick, fireHotspots = [], trafficSegments = [], center = [28.62, 77.21], showSatellite = false, showTraffic = false }: WardMapProps) {
  const wardsWithGeom = wards.filter((w) => w.geometry);
  const wardsWithoutGeom = wards.filter((w) => !w.geometry);

  return (
    <MapContainer
      center={center}
      zoom={10}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom={false}
    >
      <MapRecenter center={center} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {showSatellite && (
        <WMSTileLayer
          url={GIBS_WMS_URL}
          layers="MODIS_Terra_Aerosol"
          format="image/png"
          transparent={true}
          opacity={0.55}
          attribution="Imagery courtesy NASA GIBS / MODIS Terra"
          version="1.1.1"
        />
      )}
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
      {/* Fallback: wards without GeoJSON get a colored circle at the map center offset */}
      {wardsWithoutGeom.map((ward, i) => {
        const offset = 0.04 * (i - (wardsWithoutGeom.length - 1) / 2);
        const pos: [number, number] = [center[0] + offset, center[1] + offset];
        return (
          <CircleMarker
            key={ward.id}
            center={pos}
            radius={18}
            pathOptions={{
              fillColor: aqiFillColor(ward.avg_aqi),
              fillOpacity: 0.75,
              color: "#1e293b",
              weight: 2,
            }}
            eventHandlers={onWardClick ? { click: () => onWardClick(ward.id) } : {}}
          >
            <Popup>
              <div style={{ minWidth: 140 }}>
                <strong>{ward.name}</strong>
                <br />
                AQI: {ward.avg_aqi !== null ? ward.avg_aqi : "No data"}
                {ward.aqi_category ? ` (${ward.aqi_category})` : ""}
                <br />
                <span style={{ fontSize: 11, color: "#64748b" }}>No boundary data</span>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
      {fireHotspots.map((h) => (
        <CircleMarker
          key={h.id}
          center={[h.lat, h.lon]}
          radius={hotspotRadius(h.frp)}
          pathOptions={{
            color: hotspotColor(h.confidence),
            fillColor: hotspotColor(h.confidence),
            fillOpacity: 0.75,
            weight: 1.5,
          }}
        >
          <Popup>
            <div style={{ minWidth: 160 }}>
              <strong>🔥 Fire Detected</strong>
              <br />
              Time: {new Date(h.detected_at).toLocaleString()}
              <br />
              Confidence: {h.confidence.toFixed(0)}%{" "}
              ({h.confidence >= 75 ? "High" : "Normal"})
              <br />
              FRP: {h.frp != null ? `${h.frp.toFixed(1)} MW` : "N/A"}
              <br />
              Source: NASA FIRMS
            </div>
          </Popup>
        </CircleMarker>
      ))}

      {/* Traffic congestion segment markers */}
      {showTraffic && trafficSegments
        .filter((s) => s.lat != null && s.lon != null)
        .map((seg) => (
          <CircleMarker
            key={seg.segment_id}
            center={[seg.lat!, seg.lon!]}
            radius={10}
            pathOptions={{
              color: trafficColor(seg.congestion_ratio),
              fillColor: trafficColor(seg.congestion_ratio),
              fillOpacity: 0.85,
              weight: 2,
            }}
          >
            <Popup>
              <div style={{ minWidth: 180 }}>
                <strong>🚗 {seg.segment_name ?? seg.segment_id}</strong>
                <br />
                Congestion: <strong>{seg.congestion_ratio.toFixed(2)}×</strong>{" "}
                ({seg.congestion_ratio < 1.0 ? "Clear" : seg.congestion_ratio < 1.5 ? "Normal" : seg.congestion_ratio < 2.5 ? "Moderate" : "Heavy"})
                <br />
                Speed: {seg.current_speed != null ? `${seg.current_speed.toFixed(0)} km/h` : "—"}
                {" / "}
                {seg.free_flow_speed != null ? `${seg.free_flow_speed.toFixed(0)} km/h free-flow` : ""}
                {seg.is_mock && <><br /><span style={{ fontSize: 10, color: "#64748b" }}>Mock data — set TOMTOM_API_KEY for live</span></>}
              </div>
            </Popup>
          </CircleMarker>
        ))}

      {/* Satellite layer attribution badge */}
      {showSatellite && (
        <div
          style={{
            position: "absolute",
            top: 10,
            left: 50,
            zIndex: 1000,
            background: "rgba(15,23,42,0.85)",
            borderRadius: 6,
            padding: "4px 8px",
            fontSize: 10,
            color: "#7dd3fc",
            pointerEvents: "none",
            border: "1px solid rgba(56,189,248,0.3)",
          }}
        >
          🛰 MODIS Terra AOD overlay active
        </div>
      )}

      {/* Legend */}
      <div
        style={{
          position: "absolute",
          bottom: 24,
          right: 8,
          zIndex: 1000,
          background: "rgba(15,23,42,0.85)",
          borderRadius: 8,
          padding: "8px 12px",
          fontSize: 11,
          color: "#cbd5e1",
          pointerEvents: "none",
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: 4 }}>AQI</div>
        {[
          ["#22c55e", "Good (≤50)"],
          ["#a3e635", "Satisfactory (≤100)"],
          ["#eab308", "Moderate (≤200)"],
          ["#f97316", "Poor (≤300)"],
          ["#ef4444", "Very Poor (≤400)"],
          ["#a855f7", "Severe (>400)"],
        ].map(([color, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "inline-block", flexShrink: 0 }} />
            {label}
          </div>
        ))}
        <div style={{ fontWeight: 600, margin: "6px 0 4px" }}>Fire</div>
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", display: "inline-block", flexShrink: 0 }} />
          High confidence (≥75%)
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f97316", display: "inline-block", flexShrink: 0 }} />
          Normal confidence
        </div>
      </div>
    </MapContainer>
  );
}
