import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import RoleGuard from "@/components/RoleGuard";
import Dashboard from "@/pages/Dashboard";
import Login from "@/pages/Login";

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

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
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
                <Placeholder name="Ward Detail (Module 08)" />
              </RoleGuard>
            }
          />
          <Route
            path="/enforcement"
            element={
              <RoleGuard>
                <Placeholder name="Enforcement Queue (Module 06)" />
              </RoleGuard>
            }
          />
          <Route
            path="/advisories"
            element={
              <RoleGuard>
                <Placeholder name="Advisory Log (Module 07)" />
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
                <Placeholder name="Inspector PWA (Module 09)" />
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
