// Same-origin defaults work both with the production nginx /api proxy
// and with the local Vite /api proxy configured in vite.config.ts.
const DEFAULT_API_BASE = "/api";

const DEFAULT_WS_BASE =
  typeof window === "undefined"
    ? "ws://localhost:8080"
    : `${window.location.protocol === "https:" ? "wss" : "ws"}://${
        window.location.host
      }/api`;

export const baseUrl =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? DEFAULT_API_BASE;

export const WS_BASE =
  (import.meta.env.VITE_WS_BASE as string | undefined) ?? DEFAULT_WS_BASE;

export const FILTER_URL = `${baseUrl}/logs/tree`;
