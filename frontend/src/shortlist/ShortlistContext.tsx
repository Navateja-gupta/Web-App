import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";

interface ShortlistContextValue {
  /** True only for signed-in customers (the only role with a shortlist). */
  enabled: boolean;
  isShortlisted: (vendorId: number) => boolean;
  toggle: (vendorId: number) => Promise<void>;
}

const ShortlistContext = createContext<ShortlistContextValue | null>(null);

export function ShortlistProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const enabled = user?.role === "customer";
  const [ids, setIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!enabled) {
      setIds(new Set());
      return;
    }
    let cancelled = false;
    api
      .get<number[]>("/me/shortlist/ids")
      .then((res) => !cancelled && setIds(new Set(res.data)))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [enabled, user?.id]);

  const toggle = useCallback(
    async (vendorId: number) => {
      const saved = ids.has(vendorId);
      // Optimistic update, rolled back if the request fails.
      setIds((prev) => {
        const next = new Set(prev);
        if (saved) next.delete(vendorId);
        else next.add(vendorId);
        return next;
      });
      try {
        if (saved) await api.delete(`/me/shortlist/${vendorId}`);
        else await api.put(`/me/shortlist/${vendorId}`);
      } catch (err) {
        setIds((prev) => {
          const next = new Set(prev);
          if (saved) next.add(vendorId);
          else next.delete(vendorId);
          return next;
        });
        throw err;
      }
    },
    [ids],
  );

  const value = useMemo(() => ({ enabled, isShortlisted: (id: number) => ids.has(id), toggle }), [enabled, ids, toggle]);
  return <ShortlistContext.Provider value={value}>{children}</ShortlistContext.Provider>;
}

export function useShortlist(): ShortlistContextValue {
  const ctx = useContext(ShortlistContext);
  if (!ctx) throw new Error("useShortlist must be used inside <ShortlistProvider>");
  return ctx;
}
