import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { api } from "../lib/api";

const POLL_MS = 30_000;

/** Unread notification count, refreshed every 30 s, on navigation and when the tab regains focus. */
export function useUnreadCount(enabled: boolean): { count: number; refresh: () => void } {
  const [count, setCount] = useState(0);
  const location = useLocation();

  const refresh = useCallback(() => {
    if (!enabled) return;
    api
      .get<{ count: number }>("/me/notifications/unread-count")
      .then((r) => setCount(r.data.count))
      .catch(() => undefined);
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setCount(0);
      return;
    }
    refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, POLL_MS);
    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [enabled, refresh]);

  useEffect(() => {
    refresh();
  }, [location.pathname, refresh]);

  return { count, refresh };
}
