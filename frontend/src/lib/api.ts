import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;
if (!baseURL) {
  throw new Error("VITE_API_BASE_URL is not set. Copy frontend/.env.example to frontend/.env.");
}

/**
 * Shared API client.
 * withCredentials sends the HTTP-only auth cookies with every request.
 * The browser never sees the tokens themselves.
 */
export const api = axios.create({
  baseURL,
  withCredentials: true,
  timeout: 10_000,
});

// Requests that must never trigger an automatic token refresh.
const NO_REFRESH_PATHS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout", "/auth/token"];

// One shared refresh at a time, so parallel 401s don't each rotate the refresh token.
let refreshInFlight: Promise<void> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const path = original?.url ?? "";
    if (
      error.response?.status !== 401 ||
      !original ||
      original._retried ||
      NO_REFRESH_PATHS.some((p) => path.startsWith(p))
    ) {
      throw error;
    }

    original._retried = true;
    if (!refreshInFlight) {
      refreshInFlight = api
        .post("/auth/refresh")
        .then(() => undefined)
        .finally(() => {
          refreshInFlight = null;
        });
    }
    try {
      await refreshInFlight;
    } catch {
      throw error;
    }
    return api(original);
  },
);

/** Turn any API/network error into a message that is safe to show users. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{ loc, msg, ... }]
    if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === "string") {
      return detail[0].msg.replace(/^Value error, /, "");
    }
    if (!error.response) return "Cannot reach the server. Please check your connection.";
  }
  return "Something went wrong. Please try again.";
}
