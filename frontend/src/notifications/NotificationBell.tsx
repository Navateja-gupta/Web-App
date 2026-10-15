import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import type { AppNotification, Page } from "../types";
import { timeAgo } from "./timeAgo";
import { useUnreadCount } from "./useUnreadCount";

export default function NotificationBell() {
  const navigate = useNavigate();
  const { count, refresh } = useUnreadCount(true);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[] | null>(null);
  const [error, setError] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    setError(false);
    api
      .get<Page<AppNotification>>("/me/notifications", { params: { size: 8 } })
      .then((r) => setItems(r.data.items))
      .catch(() => setError(true));

    function onClick(e: MouseEvent) {
      if (wrapper.current && !wrapper.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function openItem(n: AppNotification) {
    setOpen(false);
    if (!n.is_read) {
      await api.post(`/me/notifications/${n.id}/read`).catch(() => undefined);
      refresh();
    }
    if (n.link) navigate(n.link);
  }

  async function markAll() {
    await api.post("/me/notifications/read-all").catch(() => undefined);
    setItems((prev) => prev?.map((n) => ({ ...n, is_read: true })) ?? null);
    refresh();
  }

  return (
    <div ref={wrapper} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={count ? `Notifications, ${count} unread` : "Notifications"}
        aria-expanded={open}
        className="relative rounded-md px-3 py-2 text-stone-700 hover:text-maroon-700"
      >
        <svg aria-hidden viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5m6 0a3 3 0 1 1-6 0m6 0H9" />
        </svg>
        {count > 0 && (
          <span className="absolute right-1 top-0.5 min-w-4 rounded-full bg-maroon-700 px-1 text-center text-[10px] font-semibold leading-4 text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-maroon-100 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-stone-100 px-4 py-2">
            <span className="text-sm font-semibold">Notifications</span>
            {count > 0 && (
              <button type="button" onClick={markAll} className="text-xs text-maroon-700 hover:underline">
                Mark all as read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {error ? (
              <p className="px-4 py-6 text-center text-sm text-red-700">Could not load notifications.</p>
            ) : !items ? (
              <p className="px-4 py-6 text-center text-sm text-stone-500">Loading…</p>
            ) : items.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-stone-500">You're all caught up.</p>
            ) : (
              <ul className="divide-y divide-stone-100">
                {items.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      onClick={() => openItem(n)}
                      className={`block w-full px-4 py-3 text-left hover:bg-maroon-50/50 ${n.is_read ? "" : "bg-amber-50/60"}`}
                    >
                      <span className="flex items-start gap-2">
                        {!n.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-maroon-600" aria-label="Unread" />}
                        <span className="min-w-0">
                          <span className="block text-sm font-medium text-stone-900">{n.title}</span>
                          <span className="line-clamp-2 block text-xs text-stone-600">{n.body}</span>
                          <span className="mt-0.5 block text-[11px] text-stone-400">{timeAgo(n.created_at)}</span>
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <Link to="/notifications" onClick={() => setOpen(false)} className="block border-t border-stone-100 px-4 py-2 text-center text-sm text-maroon-700 hover:bg-maroon-50/50">
            See all notifications
          </Link>
        </div>
      )}
    </div>
  );
}
