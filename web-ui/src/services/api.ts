import axios from "axios";

const LOCAL_API_BASE_URL = "http://localhost:8080/api/v1";
const PRODUCTION_API_BASE_URL = "/api/v1";

export function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export function resolveApiBaseUrl(
  mode: string,
  explicitBaseUrl?: string
): string {
  const configured = explicitBaseUrl?.trim();
  if (mode === "production") return PRODUCTION_API_BASE_URL;

  const allowsExplicitBaseUrl = mode === "development" || mode === "test";
  return normalizeApiBaseUrl(
    allowsExplicitBaseUrl && configured ? configured : LOCAL_API_BASE_URL
  );
}

export type ApiFailureKind = "network" | "http";

export function classifyApiFailure(error: unknown): ApiFailureKind {
  return axios.isAxiosError(error) && !error.response ? "network" : "http";
}

export const api = axios.create({
  baseURL: resolveApiBaseUrl(
    import.meta.env.PROD ? "production" : import.meta.env.MODE,
    import.meta.env.VITE_API_BASE_URL
  ),
  headers: {
    "Content-Type": "application/json",
  },
});
