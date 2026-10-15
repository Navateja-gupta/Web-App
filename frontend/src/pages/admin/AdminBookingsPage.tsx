import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Pagination from "../../components/Pagination";
import ReasonPrompt from "../../components/ReasonPrompt";
import Spinner from "../../components/Spinner";
import { BookingPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { BOOKING_LABEL, formatDate, formatINR, todayISO } from "../../lib/format";
import type { Booking, BookingStatus, Page } from "../../types";

export default function AdminBookingsPage() {
  const [status, setStatus] = useState<"" | BookingStatus>("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Booking> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<Booking>>("/admin/bookings", { params: { status: status || undefined, page, size: 20 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [status, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function complete(b: Booking) {
    if (!window.confirm(`Mark booking #${b.id} as completed?`)) return;
    try {
      await api.post(`/admin/bookings/${b.id}/complete`);
      setNotice(`Booking #${b.id} completed.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Bookings</h1>
        <p className="text-stone-600">Every status change is recorded in the audit log.</p>
      </div>
      <select
        aria-label="Filter by status"
        className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm"
        value={status}
        onChange={(e) => {
          setStatus(e.target.value as "" | BookingStatus);
          setPage(1);
        }}
      >
        <option value="">All statuses</option>
        {Object.entries(BOOKING_LABEL).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No bookings.</p>
      ) : (
        <ul className="space-y-3">
          {data.items.map((b) => (
            <li key={b.id} className="rounded-xl border border-maroon-100 bg-white p-4 text-sm shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">
                    #{b.id} · {formatDate(b.event_date)} ·{" "}
                    <Link to={`/admin/vendors/${b.vendor.id}`} className="text-maroon-700 underline">
                      {b.vendor.business_name}
                    </Link>
                  </p>
                  <p className="text-stone-600">
                    Customer: {b.customer.full_name} ({b.customer.email}) ·{" "}
                    {b.agreed_amount !== null ? formatINR(b.agreed_amount) : "amount not agreed"}
                  </p>
                  {b.cancellation_reason && <p className="text-stone-600">Reason: {b.cancellation_reason}</p>}
                </div>
                <BookingPill status={b.booking_status} />
              </div>
              {(b.booking_status === "requested" || b.booking_status === "confirmed") && cancelling !== b.id && (
                <div className="mt-2 flex gap-2">
                  {b.booking_status === "confirmed" && b.event_date <= todayISO() && (
                    <Button className="px-3 py-1.5" onClick={() => complete(b)}>
                      Mark completed
                    </Button>
                  )}
                  <Button variant="danger" className="px-3 py-1.5" onClick={() => setCancelling(b.id)}>
                    Cancel booking
                  </Button>
                </div>
              )}
              {cancelling === b.id && (
                <div className="mt-2">
                  <ReasonPrompt
                    label="Reason (shown to customer and vendor)"
                    confirmLabel="Cancel booking"
                    onCancel={() => setCancelling(null)}
                    onConfirm={async (reason) => {
                      try {
                        await api.post(`/admin/bookings/${b.id}/cancel`, { reason });
                        setCancelling(null);
                        setNotice(`Booking #${b.id} cancelled.`);
                        await load();
                      } catch (err) {
                        setError(getErrorMessage(err));
                      }
                    }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="bookings" onPage={setPage} />}
    </section>
  );
}
