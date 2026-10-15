import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import Alert from "../components/Alert";
import Button from "../components/Button";
import Pagination from "../components/Pagination";
import Spinner from "../components/Spinner";
import { api, getErrorMessage } from "../lib/api";
import { timeAgo } from "../notifications/timeAgo";
import type { AppNotification, Page } from "../types";

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<AppNotification> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<AppNotification>>("/me/notifications", { params: { unread_only: unreadOnly, page, size: 20 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [unreadOnly, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function open(n: AppNotification) {
    if (!n.is_read) await api.post(`/me/notifications/${n.id}/read`).catch(() => undefined);
    if (n.link) navigate(n.link);
    else void load();
  }

  return (
    <section className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">Notifications</h1>
          <p className="text-stone-600">Updates about your enquiries, quotations, bookings and listings.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-stone-700">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => {
                setUnreadOnly(e.target.checked);
                setPage(1);
              }}
            />
            Unread only
          </label>
          <Button
            variant="secondary"
            onClick={async () => {
              await api.post("/me/notifications/read-all").catch(() => undefined);
              void load();
            }}
          >
            Mark all as read
          </Button>
        </div>
      </div>
      {error && <Alert kind="error">{error}</Alert>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No notifications.</p>
      ) : (
        <ul className="divide-y divide-stone-100 overflow-hidden rounded-xl border border-maroon-100 bg-white">
          {data.items.map((n) => (
            <li key={n.id}>
              <button type="button" onClick={() => open(n)} className={`block w-full px-5 py-4 text-left hover:bg-maroon-50/50 ${n.is_read ? "" : "bg-amber-50/60"}`}>
                <span className="flex items-start gap-3">
                  {!n.is_read && <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-maroon-600" aria-label="Unread" />}
                  <span>
                    <span className="block font-medium text-stone-900">{n.title}</span>
                    <span className="block whitespace-pre-line text-sm text-stone-600">{n.body}</span>
                    <span className="mt-1 block text-xs text-stone-400">{timeAgo(n.created_at)}</span>
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="notifications" onPage={setPage} />}
    </section>
  );
}
