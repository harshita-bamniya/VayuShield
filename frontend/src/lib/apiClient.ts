import axios, { AxiosInstance, AxiosResponse } from "axios";
import type { ApiEnvelope } from "./types";
import { API_BASE } from "./constants";

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from localStorage on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Unwrap the envelope; throw on error field
client.interceptors.response.use(
  (response: AxiosResponse<ApiEnvelope<unknown>>) => {
    if (response.data.error) {
      throw Object.assign(new Error(response.data.error.message), {
        code: response.data.error.code,
        details: response.data.error.details,
      });
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default client;
