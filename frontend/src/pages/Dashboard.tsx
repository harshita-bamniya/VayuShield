import { useNavigate, NavLink } from "react-router-dom";
import { useAuth } from "@/features/auth/useAuth";

const STAT_CARDS = [
  { label: "City AQI", value: "—", unit: "", desc: "Delhi · Live", color: "text-yellow-400" },
  { label: "Active Alerts", value: "—", unit: "", desc: "Pending review", color: "text-red-400" },
  { label: "Pending Inspections", value: "—", unit: "", desc: "In queue", color: "text-orange-400" },
  { label: "Advisories Sent", value: "—", unit: "", desc: "Last 24 h", color: "text-green-400" },
];

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/enforcement", label: "Enforcement", icon: "🚨" },
  { to: "/advisories", label: "Advisories", icon: "📢" },
  { to: "/admin/cities", label: "City Admin", icon: "🏙️" },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

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
          <h1 className="text-lg font-semibold text-white">Dashboard</h1>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live data
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {STAT_CARDS.map((card) => (
              <div
                key={card.label}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5"
              >
                <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">
                  {card.label}
                </p>
                <p className={`text-3xl font-bold ${card.color} mb-1`}>
                  {card.value}
                </p>
                <p className="text-xs text-slate-500">{card.desc}</p>
              </div>
            ))}
          </div>

          {/* Placeholder map/chart area */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex items-center justify-center min-h-64">
            <div className="text-center text-slate-600">
              <p className="text-4xl mb-3">🗺️</p>
              <p className="text-sm font-medium">Attribution Map</p>
              <p className="text-xs mt-1">Available in Module 08 — Admin Dashboard</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
