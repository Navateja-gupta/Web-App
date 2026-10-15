import { useEffect, useState } from "react";

import { api, getErrorMessage } from "../lib/api";

type CheckState = { status: "loading" } | { status: "ok"; label: string } | { status: "error"; message: string };

function useHealthCheck(path: string, okLabel: string): CheckState {
  const [state, setState] = useState<CheckState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .get(path)
      .then(() => !cancelled && setState({ status: "ok", label: okLabel }))
      .catch((err) => !cancelled && setState({ status: "error", message: getErrorMessage(err) }));
    return () => {
      cancelled = true;
    };
  }, [path, okLabel]);

  return state;
}

function StatusRow({ name, state }: { name: string; state: CheckState }) {
  const styles = {
    loading: "bg-stone-100 text-stone-600",
    ok: "bg-green-100 text-green-800",
    error: "bg-red-100 text-red-800",
  }[state.status];
  const text = state.status === "loading" ? "Checking…" : state.status === "ok" ? state.label : state.message;

  return (
    <li className="flex items-center justify-between gap-4 py-3">
      <span className="font-medium">{name}</span>
      <span className={`rounded-full px-3 py-1 text-sm ${styles}`}>{text}</span>
    </li>
  );
}

export default function HomePage() {
  const apiStatus = useHealthCheck("/health", "Running");
  const dbStatus = useHealthCheck("/health/db", "Connected");

  return (
    <section className="mx-auto max-w-xl">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">All your wedding services in one place</h1>
      <p className="mt-3 text-stone-600">
        The marketplace is being set up. This page shows whether the frontend can reach the backend and database.
      </p>

      <div className="mt-8 rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">System status</h2>
        <ul className="mt-2 divide-y divide-stone-100" aria-live="polite">
          <StatusRow name="Backend API" state={apiStatus} />
          <StatusRow name="Database" state={dbStatus} />
        </ul>
      </div>
    </section>
  );
}
