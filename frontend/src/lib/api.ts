import axios, { AxiosError } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;
if (!baseURL) {
  throw new Error("VITE_API_BASE_URL is not set. Copy frontend/.env.example to frontend/.env.");
}

/**
 * Shared API client.
 * withCredentials sends the HTTP-only auth cookie (added in Phase 2) with every request.
 */
export const api = axios.create({
  baseURL,
  withCredentials: true,
  timeout: 10_000,
});

/** Turn any API/network error into a message that is safe to show users. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (!error.response) return "Cannot reach the server. Please check your connection.";
  }
  return "Something went wrong. Please try again.";
}
