import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { getErrorMessage } from "../lib/api";
import { useShortlist } from "../shortlist/ShortlistContext";

/**
 * Save/unsave a vendor. Anonymous visitors are sent to log in; vendors and admins
 * (who have no shortlist) see nothing.
 */
export default function ShortlistButton({ vendorId, compact = false }: { vendorId: number; compact?: boolean }) {
  const { user } = useAuth();
  const { enabled, isShortlisted, toggle } = useShortlist();
  const location = useLocation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const base = `inline-flex items-center gap-1.5 rounded-full border text-sm font-medium transition ${compact ? "px-2.5 py-1" : "px-4 py-2"}`;

  if (!user) {
    return (
      <Link
        to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`}
        className={`${base} border-stone-300 bg-white text-stone-700 hover:border-maroon-300`}
        title="Log in to save vendors"
      >
        <span aria-hidden>♡</span> Save
      </Link>
    );
  }
  if (!enabled) return null;

  const saved = isShortlisted(vendorId);

  async function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setBusy(true);
    setError(null);
    try {
      await toggle(vendorId);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-end">
      <button
        type="button"
        onClick={handleClick}
        disabled={busy}
        aria-pressed={saved}
        className={`${base} ${saved ? "border-maroon-600 bg-maroon-50 text-maroon-800" : "border-stone-300 bg-white text-stone-700 hover:border-maroon-300"}`}
      >
        <span aria-hidden>{saved ? "♥" : "♡"}</span> {saved ? "Saved" : "Save"}
      </button>
      {error && <span className="mt-1 text-xs text-red-700">{error}</span>}
    </span>
  );
}
