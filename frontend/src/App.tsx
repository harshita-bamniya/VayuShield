import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import RoleGuard from "@/components/RoleGuard";
import client from "@/lib/apiClient";
import { useAuth } from "@/features/auth/useAuth";
import Advisories from "@/pages/Advisories";
import Dashboard from "@/pages/Dashboard";
import Enforcement from "@/pages/Enforcement";
import Login from "@/pages/Login";
import WardDetail from "@/pages/WardDetail";
import InspectorPage from "@/pages/InspectorPage";
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
                <Dashboard />
              </RoleGuard>
            }
          />
          <Route
            path="/wards/:id"
            element={
              <RoleGuard>
                <WardDetail />
              </RoleGuard>
            }
          />
          <Route
            path="/enforcement"
            element={
              <RoleGuard>
                <Enforcement />
              </RoleGuard>
            }
          />
          <Route
            path="/advisories"
            element={
              <RoleGuard>
                <Advisories />
              </RoleGuard>
            }
          />
          <Route
            path="/admin/cities"
            element={
              <RoleGuard roles={["sysadmin"]}>
                <Placeholder name="City Onboarding (Module 11)" />
              </RoleGuard>
            }
          />
          <Route
            path="/inspector"
            element={
              <RoleGuard roles={["inspector", "sysadmin"]}>
                <InspectorPage />
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
