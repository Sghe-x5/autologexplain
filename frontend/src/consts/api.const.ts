// Prod defaults; override in frontend/.env.local via VITE_API_BASE / VITE_WS_BASE.
const PROD_API_BASE = "http://84.201.181.1/api";
const PROD_WS_BASE = "ws://84.201.181.1/api";

export const baseUrl =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? PROD_API_BASE;

export const WS_BASE =
  (import.meta.env.VITE_WS_BASE as string | undefined) ?? PROD_WS_BASE;

export const FILTER_URL = `${baseUrl}/logs/tree`;
