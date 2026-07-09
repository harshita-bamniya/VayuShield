import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import {
  fetchCities,
  fetchWards,
  fetchStations,
  createCity,
  createWard,
  createStation,
  type CityWithCounts,
  type StationOut,
  type CreateCityPayload,
  type CreateWardPayload,
  type CreateStationPayload,
} from "@/features/cities/api";
import type { Ward } from "@/lib/types";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/enforcement", label: "Enforcement", icon: "🚨" },
  { to: "/advisories", label: "Advisories", icon: "📢" },
  { to: "/admin/cities", label: "City Admin", icon: "🏙️" },
];

const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Colombo",
  "Asia/Karachi",
  "Asia/Dhaka",
  "Asia/Kathmandu",
  "UTC",
];

// ── Add City Form ─────────────────────────────────────────────────────────────

function AddCityForm({ onCreated }: { onCreated: (city: CityWithCounts) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [state, setState] = useState("");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [configText, setConfigText] = useState("");
  const [configError, setConfigError] = useState("");

  const mutation = useMutation({
    mutationFn: (p: CreateCityPayload) => createCity(p),
    onSuccess: (city) => {
      qc.invalidateQueries({ queryKey: ["admin-cities"] });
      onCreated(city);
      setName("");
      setState("");
      setTimezone("Asia/Kolkata");
      setConfigText("");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setConfigError("");
    let config_json: Record<string, unknown> = {};
    if (configText.trim()) {
      try {
        config_json = JSON.parse(configText);
      } catch {
        setConfigError("Invalid JSON");
        return;
      }
    }
    mutation.mutate({ name, state, timezone, config_json });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">City name *</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Mumbai"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">State *</label>
          <input
            required
            value={state}
            onChange={(e) => setState(e.target.value)}
            placeholder="e.g. Maharashtra"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>
      <div>
        <label className="block text-xs text-slate-400 mb-1">Timezone</label>
        <select
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-sky-500"
        >
          {TIMEZONES.map((tz) => (
            <option key={tz} value={tz}>
              {tz}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-slate-400 mb-1">Config JSON (optional)</label>
        <textarea
          value={configText}
          onChange={(e) => setConfigText(e.target.value)}
          placeholder='{"key": "value"}'
          rows={3}
          className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-sky-500 resize-none"
        />
        {configError && <p className="text-red-400 text-xs mt-1">{configError}</p>}
      </div>
      {mutation.isError && (
        <p className="text-red-400 text-xs">{String((mutation.error as Error).message)}</p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded transition-colors"
      >
        {mutation.isPending ? "Creating…" : "Create City"}
      </button>
    </form>
  );
}

// ── Add Ward Form ─────────────────────────────────────────────────────────────

function AddWardForm({ cityId, onCreated }: { cityId: string; onCreated: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [population, setPopulation] = useState("");
  const [geojsonText, setGeojsonText] = useState("");
  const [geoError, setGeoError] = useState("");

  const mutation = useMutation({
    mutationFn: (p: CreateWardPayload) => createWard(cityId, p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-wards", cityId] });
      onCreated();
      setName("");
      setPopulation("");
      setGeojsonText("");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGeoError("");
    let geometry: Record<string, unknown> | null = null;
    if (geojsonText.trim()) {
      try {
        geometry = JSON.parse(geojsonText);
      } catch {
        setGeoError("Invalid GeoJSON");
        return;
      }
    }
    mutation.mutate({
      name,
      population: population ? parseInt(population, 10) : null,
      geometry,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 mt-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Ward name *</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Bandra"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Population</label>
          <input
            type="number"
            min={0}
            value={population}
            onChange={(e) => setPopulation(e.target.value)}
            placeholder="e.g. 500000"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>
      <div>
        <label className="block text-xs text-slate-400 mb-1">
          Geometry — paste GeoJSON MultiPolygon (optional)
        </label>
        <textarea
          value={geojsonText}
          onChange={(e) => setGeojsonText(e.target.value)}
          placeholder='{"type":"MultiPolygon","coordinates":[[[[77.2,28.6],[77.3,28.6],[77.3,28.7],[77.2,28.7],[77.2,28.6]]]]}'
          rows={4}
          className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-emerald-500 resize-none"
        />
        {geoError && <p className="text-red-400 text-xs mt-1">{geoError}</p>}
      </div>
      {mutation.isError && (
        <p className="text-red-400 text-xs">{String((mutation.error as Error).message)}</p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded transition-colors"
      >
        {mutation.isPending ? "Adding…" : "Add Ward"}
      </button>
    </form>
  );
}

// ── Add Station Form ──────────────────────────────────────────────────────────

function AddStationForm({ cityId, wards, onCreated }: { cityId: string; wards: Ward[]; onCreated: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [wardId, setWardId] = useState("");

  const mutation = useMutation({
    mutationFn: (p: CreateStationPayload) => createStation(cityId, p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-stations", cityId] });
      onCreated();
      setName("");
      setCode("");
      setLat("");
      setLng("");
      setWardId("");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const geometry =
      lat && lng
        ? { type: "Point", coordinates: [parseFloat(lng), parseFloat(lat)] }
        : null;
    mutation.mutate({
      name,
      external_station_code: code,
      geometry,
      ward_id: wardId || null,
      is_active: true,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 mt-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Station name *</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Andheri CAAQMS"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Station code *</label>
          <input
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="e.g. MPCB_ANDHERI"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Latitude</label>
          <input
            type="number"
            step="any"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            placeholder="e.g. 19.1136"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Longitude</label>
          <input
            type="number"
            step="any"
            value={lng}
            onChange={(e) => setLng(e.target.value)}
            placeholder="e.g. 72.8697"
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
        </div>
      </div>
      {wards.length > 0 && (
        <div>
          <label className="block text-xs text-slate-400 mb-1">Assign to ward (optional)</label>
          <select
            value={wardId}
            onChange={(e) => setWardId(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-violet-500"
          >
            <option value="">— None —</option>
            {wards.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {mutation.isError && (
        <p className="text-red-400 text-xs">{String((mutation.error as Error).message)}</p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded transition-colors"
      >
        {mutation.isPending ? "Adding…" : "Add Station"}
      </button>
    </form>
  );
}

// ── City Row (expanded detail) ────────────────────────────────────────────────

function CityRow({ city }: { city: CityWithCounts }) {
  const [open, setOpen] = useState(false);
  const [addingWard, setAddingWard] = useState(false);
  const [addingStation, setAddingStation] = useState(false);

  const wardsQ = useQuery({
    queryKey: ["admin-wards", city.id],
    queryFn: () => fetchWards(city.id),
    enabled: open,
  });

  const stationsQ = useQuery<StationOut[]>({
    queryKey: ["admin-stations", city.id],
    queryFn: () => fetchStations(city.id),
    enabled: open,
  });

  const wardCount = wardsQ.data?.length ?? "—";
  const stationCount = stationsQ.data?.length ?? "—";

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-4 px-4 py-3 text-left hover:bg-slate-700/40 transition-colors"
      >
        <span className="text-lg">{open ? "▾" : "▸"}</span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white truncate">{city.name}</p>
          <p className="text-xs text-slate-400">
            {city.state} · {city.timezone}
          </p>
        </div>
        <div className="flex gap-4 text-xs text-slate-400 shrink-0">
          <span>
            <span className="text-white font-semibold">{wardCount}</span> wards
          </span>
          <span>
            <span className="text-white font-semibold">{stationCount}</span> stations
          </span>
          <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400 border border-green-500/30 text-xs font-semibold uppercase">
            active
          </span>
        </div>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-slate-700 px-4 py-4 space-y-5">
          {/* Wards section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-slate-200">Wards</h4>
              <button
                onClick={() => setAddingWard((v) => !v)}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium"
              >
                {addingWard ? "Cancel" : "+ Add Ward"}
              </button>
            </div>
            {wardsQ.isLoading && <p className="text-xs text-slate-500">Loading…</p>}
            {wardsQ.data && wardsQ.data.length === 0 && (
              <p className="text-xs text-slate-500 italic">No wards yet.</p>
            )}
            {wardsQ.data && wardsQ.data.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b border-slate-700">
                      <th className="pb-1 font-medium">Name</th>
                      <th className="pb-1 font-medium">Population</th>
                      <th className="pb-1 font-medium">Geometry</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wardsQ.data.map((w) => (
                      <tr key={w.id} className="border-b border-slate-700/50 last:border-0">
                        <td className="py-1.5 text-white">{w.name}</td>
                        <td className="py-1.5 text-slate-300">
                          {w.population ? w.population.toLocaleString() : "—"}
                        </td>
                        <td className="py-1.5 text-slate-400 text-xs">
                          {(w as unknown as Record<string, unknown>).geometry ? "✓ GeoJSON" : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {addingWard && (
              <AddWardForm
                cityId={city.id}
                onCreated={() => setAddingWard(false)}
              />
            )}
          </div>

          {/* Stations section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-slate-200">Stations</h4>
              <button
                onClick={() => setAddingStation((v) => !v)}
                className="text-xs text-violet-400 hover:text-violet-300 font-medium"
              >
                {addingStation ? "Cancel" : "+ Add Station"}
              </button>
            </div>
            {stationsQ.isLoading && <p className="text-xs text-slate-500">Loading…</p>}
            {stationsQ.data && stationsQ.data.length === 0 && (
              <p className="text-xs text-slate-500 italic">No stations yet.</p>
            )}
            {stationsQ.data && stationsQ.data.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b border-slate-700">
                      <th className="pb-1 font-medium">Name</th>
                      <th className="pb-1 font-medium">Code</th>
                      <th className="pb-1 font-medium">Coords</th>
                      <th className="pb-1 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stationsQ.data.map((s) => {
                      const geo = s.geometry as Record<string, unknown> | null;
                      const coords = geo?.coordinates as number[] | null;
                      return (
                        <tr key={s.id} className="border-b border-slate-700/50 last:border-0">
                          <td className="py-1.5 text-white">{s.name}</td>
                          <td className="py-1.5 text-slate-400 font-mono text-xs">
                            {s.external_station_code}
                          </td>
                          <td className="py-1.5 text-slate-400 text-xs">
                            {coords ? `${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}` : "—"}
                          </td>
                          <td className="py-1.5">
                            <span
                              className={`text-xs font-semibold ${
                                s.is_active ? "text-green-400" : "text-slate-500"
                              }`}
                            >
                              {s.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {addingStation && (
              <AddStationForm
                cityId={city.id}
                wards={wardsQ.data ?? []}
                onCreated={() => setAddingStation(false)}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminCitiesPage() {
  const user = useAuth((s) => s.user);
  const [showAddCity, setShowAddCity] = useState(false);

  const citiesQ = useQuery({
    queryKey: ["admin-cities"],
    queryFn: fetchCities,
  });

  function handleCityCreated(city: CityWithCounts) {
    setShowAddCity(false);
    // queryClient is invalidated inside AddCityForm
    console.log("Created city:", city.id);
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white flex">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="px-5 py-4 border-b border-slate-700">
          <p className="text-sky-400 font-bold text-lg tracking-tight">VayuShield</p>
          <p className="text-slate-500 text-xs">AI Platform</p>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-sky-500/20 text-sky-400 font-medium"
                    : "text-slate-400 hover:text-white hover:bg-slate-700"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-slate-700 text-xs text-slate-500">
          {user?.email}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="px-8 py-6 max-w-4xl">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-white">City Onboarding</h1>
              <p className="text-slate-400 text-sm mt-1">
                Manage cities, wards, and monitoring stations
              </p>
            </div>
            <button
              onClick={() => setShowAddCity((v) => !v)}
              className="bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {showAddCity ? "Cancel" : "+ Add City"}
            </button>
          </div>

          {/* Add City Form */}
          {showAddCity && (
            <div className="mb-6 bg-slate-800 border border-slate-700 rounded-xl p-5">
              <h3 className="text-base font-semibold text-white mb-4">New City</h3>
              <AddCityForm onCreated={handleCityCreated} />
            </div>
          )}

          {/* City list */}
          {citiesQ.isLoading && (
            <div className="text-slate-400 text-sm py-8 text-center">Loading cities…</div>
          )}
          {citiesQ.isError && (
            <div className="text-red-400 text-sm py-4">Failed to load cities.</div>
          )}
          {citiesQ.data && citiesQ.data.length === 0 && (
            <div className="text-slate-500 text-sm py-8 text-center italic">
              No cities yet. Click "+ Add City" to onboard the first city.
            </div>
          )}
          <div className="space-y-3">
            {citiesQ.data?.map((city) => (
              <CityRow key={city.id} city={city} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
