import { create } from "zustand";
import { login as apiLogin, logout as apiLogout } from "./api";
import type { UserOut } from "@/lib/types";

interface AuthState {
  user: UserOut | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const tokens = await apiLogin(email, password);
      set({ user: tokens.user, isAuthenticated: true, isLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    await apiLogout();
    set({ user: null, isAuthenticated: false });
  },

  clearError: () => set({ error: null }),
}));
