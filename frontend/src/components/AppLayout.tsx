import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/useAuth";

const NAV_ITEMS = [
  { to: "/dashboard",    label: "Dashboard",      icon: "📊", sysadmin: false },
  { to: "/compare",      label: "Compare Cities", icon: "🗺️", sysadmin: true  },
  { to: "/enforcement",  label: "Enforcement",    icon: "🚨", sysadmin: false },
  { to: "/advisories",   label: "Advisories",     icon: "📢", sysadmin: false },
  { to: "/reports",      label: "Reports",        icon: "📄", sysadmin: false },
  { to: "/admin/cities", label: "City Admin",     icon: "🏙️", sysadmin: false },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isSysadmin = user?.role === "sysadmin";

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
          {NAV_ITEMS.filter((item) => !item.sysadmin || isSysadmin).map((item) => (
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

      {/* Page content */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
}
