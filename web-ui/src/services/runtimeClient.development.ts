import { ApiNflDataClient, resolveApiBaseUrl } from "./apiDataClient";

export const dataClient = new ApiNflDataClient(
  resolveApiBaseUrl(import.meta.env.MODE, import.meta.env.VITE_API_BASE_URL)
);
