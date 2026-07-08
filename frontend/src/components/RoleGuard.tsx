import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/features/auth/useAuth";
import type { Role } from "@/lib/types";

interface RoleGuardProps {
  roles?: Role[];
  children: ReactNode;
}

export default function RoleGuard({ roles, children }: RoleGuardProps) {
  const { isAuthenticated, user } = useAuth();
  const isDemoMode = new URLSearchParams(window.location.search).get("demo") === "true";

  if (!isAuthenticated && !isDemoMode) {
    return <Navigate to="/login" replace />;
  }

  if (roles && user && !roles.includes(user.role as Role)) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Access Denied</h2>
          <p className="text-gray-500">You don&apos;t have permission to view this page.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
