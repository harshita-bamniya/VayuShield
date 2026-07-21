import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import RoleGuard from "@/components/RoleGuard";
import AppLayout from "@/components/AppLayout";
import client from "@/lib/apiClient";
import { useAuth } from "@/features/auth/useAuth";
import Advisories from "@/pages/Advisories";
import Dashboard from "@/pages/Dashboard";
import Enforcement from "@/pages/Enforcement";
import Login from "@/pages/Login";
import WardDetail from "@/pages/WardDetail";
import InspectorPage from "@/pages/InspectorPage";
import AdminCitiesPage from "@/pages/AdminCitiesPage";
import ReportsPage from "@/pages/ReportsPage";
import PublicCityPage from "@/pages/PublicCityPage";
import ComparePage from "@/pages/ComparePage";
import type { UserOut } from "@/lib/types";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

function Placeholder({ name }: { name: string }) {
  return (
    <div style={{ padding: 32 }}>
      <h2>{name}</h2>
      <p>Module not yet implemented.</p>
    </div>
  );
}

/** Re-hydrates the Zustand auth store on page load by calling /users/me if a token exists. */
function AuthRehydrator() {
  const isAuthenticated = useAuth((s) => s.isAuthenticated);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token || isAuthenticated) return;

    client
      .get<{ data: UserOut }>("/users/me")
      .then((resp) => {
        const user = resp.data.data;
        if (user) {
          useAuth.setState({ user, isAuthenticated: true });
        }
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthRehydrator />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <RoleGuard>
                <AppLayout><Dashboard /></AppLayout>
              </RoleGuard>
            }
          />
          <Route
            path="/wards/:id"
            element={
              <RoleGuard>
                <AppLayout><WardDetail /></AppLayout>
              </RoleGuard>
            }
          />
          <Route
            path="/enforcement"
            element={
              <RoleGuard>
                <AppLayout><Enforcement /></AppLayout>
              </RoleGuard>
            }
          />
          <Route
            path="/advisories"
            element={
              <RoleGuard>
                <AppLayout><Advisories /></AppLayout>
              </RoleGuard>
            }
          />
          <Route
            path="/admin/cities"
            element={
              <RoleGuard roles={["sysadmin"]}>
                <AppLayout><AdminCitiesPage /></AppLayout>
              </RoleGuard>
            }
          />
          <Route
            path="/reports"
            element={
              <RoleGuard roles={["admin", "sysadmin"]}>
                <AppLayout><ReportsPage /></AppLayout>
              </RoleGuard>
            }
          />
          <Route
            path="/inspector"
            element={
              <RoleGuard roles={["inspector", "sysadmin"]}>
                <AppLayout><InspectorPage /></AppLayout>
              </RoleGuard>
            }
          />
          <Route path="/city/:cityId/public" element={<PublicCityPage />} />
          <Route
            path="/compare"
            element={
              <RoleGuard roles={["sysadmin"]}>
                <AppLayout><ComparePage /></AppLayout>
              </RoleGuard>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Placeholder name="404 — Page not found" />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
