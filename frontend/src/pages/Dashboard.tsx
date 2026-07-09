import { useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/useAuth";
import { useCities } from "@/features/cities/useCities";
import { fetchCities, fetchCity } from "@/features/cities/api";
import { fetchForecast } from "@/features/forecast/api";
import ForecastChart from "@/features/forecast/ForecastChart";
import { fetchPendingCount } from "@/features/enforcement/api";
import { fetchAdvisoryCount } from "@/features/advisory/api";
import { fetchWardsWithAqi } from "@/features/wards/api";
import WardMap from "@/components/WardMap";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/enforcement", label: "Enforcement", icon: "🚨" },
  { to: "/advisories", label: "Advisories", icon: "📢" },
  { to: "/reports", label: "Reports", icon: "📄" },
  { to: "/admin/cities", label: "City Admin", icon: "🏙️" },
];

function aqiCategory(aqi: number): string {
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

function aqiColor(aqi: number): string {
  if (aqi <= 50) return "text-green-400";
  if (aqi <= 100) return "text-lime-400";
  if (aqi <= 200) return "text-yellow-400";
  if (aqi <= 300) return "text-orange-400";
  if (aqi <= 400) return "text-red-400";
  return "text-purple-400";
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { selectedCityId, selectedCity, setSelectedCity } = useCities();

  const isSysadmin = user?.role === "sysadmin";

  const { data: cities } = useQuery({
    queryKey: ["cities"],
    queryFn: fetchCities,
    enabled: isSysadmin,
  });

  const { data: userCity } = useQuery({
    queryKey: ["city", user?.city_id],
    queryFn: () => fetchCity(user!.city_id!),
    enabled: !isSysadmin && !!user?.city_id,
  });

  useEffect(() => {
    if (!selectedCityId) {
      if (userCity) setSelectedCity(userCity);
      else if (cities && cities.length > 0) setSelectedCity(cities[0]);
    }
  }, [cities, userCity, selectedCityId, setSelectedCity]);

  // Forecast query — runs once city is selected
  const { data: forecast, isLoading: forecastLoading } = useQuery({
    queryKey: ["forecast", selectedCityId],
    queryFn: () => fetchForecast(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 15, // treat fresh for 15 min
  });

  const { data: pendingCount } = useQuery({
    queryKey: ["enforcement-count", selectedCityId],
    queryFn: () => fetchPendingCount(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const { data: advisoryCount } = useQuery({
    queryKey: ["advisory-count", selectedCityId],
    queryFn: () => fetchAdvisoryCount(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const { data: wards = [] } = useQuery({
    queryKey: ["wards-aqi", selectedCityId],
    queryFn: () => fetchWardsWithAqi(selectedCityId!),
    enabled: !!selectedCityId,
    staleTime: 1000 * 60 * 5,
  });

  const displayCity = selectedCity;
  const currentAqi = forecast?.points[0]?.predicted_aqi;

  const statCards = [
    {
      label: "City AQI",
      value: currentAqi != null ? String(currentAqi) : "—",
      desc: currentAqi != null ? aqiCategory(currentAqi) : "Loading…",
      color: currentAqi != null ? aqiColor(currentAqi) : "text-slate-400",
    },
    {
      label: "Peak Forecast AQI",
      value: forecast?.peak_aqi != null ? String(forecast.peak_aqi) : "—",
      desc: "Next 72 hours",
      color: forecast?.peak_aqi != null ? aqiColor(forecast.peak_aqi) : "text-slate-400",
    },
    {
      label: "Pending Inspections",
      value: pendingCount != null ? String(pendingCount) : "—",
      desc: "In queue",
      color: "text-orange-400",
    },
    {
      label: "Advisories Sent",
      value: advisoryCount != null ? String(advisoryCount) : "—",
      desc: "Total issued",
      color: "text-green-400",
    },
  ];

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
            <div className="w-8 h-8 rounded-lg bg-blue-500 bg-opacity-20 border border-blue-400 border-opacity-40 flex items-center justify-center text-sm">
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
                    ? "bg-blue-500 bg-opacity-20 text-blue-300"
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
            <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs bg-blue-500 bg-opacity-20 text-blue-400 uppercase tracking-wide font-semibold">
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
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-white">Dashboard</h1>
            {displayCity && (
              <span className="px-2 py-0.5 rounded-md text-xs bg-slate-800 text-slate-400 border border-slate-700">
                {displayCity.name}, {displayCity.state}
              </span>
            )}
          </div>
          {isSysadmin && cities && cities.length > 1 && (
            <select
              className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={selectedCityId ?? ""}
              onChange={(e) => {
                const city = cities.find((c) => c.id === e.target.value);
                if (city) setSelectedCity(city);
              }}
            >
              {cities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live data
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {statCards.map((card) => (
              <div
                key={card.label}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5"
              >
                <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">
                  {card.label}
                </p>
                <p className={`text-3xl font-bold ${card.color} mb-1`}>{card.value}</p>
                <p className="text-xs text-slate-500">
                  {displayCity ? `${displayCity.name} · ` : ""}
                  {card.desc}
                </p>
              </div>
            ))}
          </div>

          {/* Ward map + forecast side by side */}
          <div className="grid lg:grid-cols-2 gap-4 mb-4">
            {/* Ward AQI map */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden" style={{ height: 340 }}>
              <div className="px-4 pt-3 pb-2 border-b border-slate-800">
                <p className="text-sm font-semibold text-slate-200">Ward AQI Map</p>
                <p className="text-xs text-slate-500">Click a ward to view details</p>
              </div>
              <div style={{ height: 290 }}>
                {wards.length > 0 ? (
                  <WardMap wards={wards} onWardClick={(wardId) => navigate(`/wards/${wardId}`)} />
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-600 text-sm">
                    {selectedCityId ? "Loading wards…" : "Select a city"}
                  </div>
                )}
              </div>
            </div>

            {/* Forecast chart */}
            {forecastLoading || !selectedCityId ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex items-center justify-center min-h-64">
                <div className="text-center text-slate-600">
                  <p className="text-4xl mb-3">📈</p>
                  <p className="text-sm font-medium">
                    {selectedCityId ? "Loading forecast…" : "Select a city to see the forecast"}
                  </p>
                </div>
              </div>
            ) : forecast ? (
              <ForecastChart
                points={forecast.points}
                generatedAt={forecast.generated_at}
                peakAqi={forecast.peak_aqi}
              />
            ) : null}
          </div>
        </main>
      </div>
    </div>
  );
}
