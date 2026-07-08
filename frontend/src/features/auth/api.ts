import client from "@/lib/apiClient";
import type { UserOut } from "@/lib/types";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserOut;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const resp = await client.post<{ data: TokenResponse }>("/auth/login", { email, password });
  const tokens = resp.data.data!;
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
  return tokens;
}

export async function logout(): Promise<void> {
  await client.post("/auth/logout").catch(() => {});
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function refreshToken(): Promise<string> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) throw new Error("No refresh token");
  const resp = await client.post<{ data: { access_token: string } }>("/auth/refresh", {
    refresh_token: refresh,
  });
  const newAccess = resp.data.data!.access_token;
  localStorage.setItem("access_token", newAccess);
  return newAccess;
}
