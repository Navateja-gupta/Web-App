import { useCallback, useEffect, useState } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import Pagination from "../../components/Pagination";
import ReasonPrompt from "../../components/ReasonPrompt";
import Spinner from "../../components/Spinner";
import { BookingPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { BOOKING_LABEL, formatDate, formatINR, todayISO } from "../../lib/format";
import type { Booking, BookingStatus, Page } from "../../types";

type Mode = { id: number; kind: "confirm" | "reject" | "cancel" } | null;

export default function VendorBookings() {
  const [status, setStatus] = useState<"" | BookingStatus>("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Booking> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>(null);
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<Booking>>("/me/vendor/bookings", { params: { status: status || undefined, page, size: 10 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [status, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(booking: Booking, action: string, body: object, success: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.post(`/me/vendor/bookings/${booking.id}/${action}`, body);
      setMode(null);
      setNotice(success);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <label className="text-sm text-stone-700">
        Show{" "}
        <select
          className="ml-1 rounded-lg border border-stone-300 bg-white px-2 py-1.5"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as "" | BookingStatus);
            setPage(1);
          }}
        >
          <option value="">All bookings</option>
          {Object.entries(BOOKING_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No bookings here.</p>
      ) : (
        <ul className="space-y-4">
          {data.items.map((b) => (
            <li key={b.id} className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    {formatDate(b.event_date)}
                    {b.event_location ? ` · ${b.event_location}` : ""}
                  </p>
                  <p className="text-sm">
                    {b.customer.full_name} ·{" "}
                    <a href={`mailto:${b.customer.email}`} className="text-maroon-700 underline">
                      {b.customer.email}
                    </a>
                    {b.customer.phone && (
                      <>
                        {" · "}
                        <a href={`tel:${b.customer.phone}`} className="text-maroon-700 underline">
                          {b.customer.phone}
                        </a>
                      </>
                    )}
                  </p>
                  <p className="text-sm text-stone-600">
                    {b.package ? `${b.package.name} · ` : ""}
                    {b.agreed_amount !== null ? `Agreed ${formatINR(b.agreed_amount)}` : "Amount not agreed yet"}
                    {b.quotation_id ? " · from your quotation" : ""}
                  </p>
                  {b.notes && <p className="mt-1 text-sm text-stone-600">Note: {b.notes}</p>}
                  {b.cancellation_reason && <p className="mt-1 text-sm text-stone-600">Reason: {b.cancellation_reason}</p>}
                </div>
                <BookingPill status={b.booking_status} />
              </div>

              {!mode && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {b.booking_status === "requested" && (
                    <>
                      <Button
                        onClick={() => {
                          setAmount(b.agreed_amount !== null ? String(b.agreed_amount) : "");
                          setMode({ id: b.id, kind: "confirm" });
                        }}
                      >
                        Confirm booking
                      </Button>
                      <Button variant="secondary" onClick={() => setMode({ id: b.id, kind: "reject" })}>
                        Not available
                      </Button>
                    </>
                  )}
                  {b.booking_status === "confirmed" && (
                    <>
                      {b.event_date <= todayISO() && (
                        <Button loading={busy} onClick={() => act(b, "complete", {}, "Booking marked as completed. The customer can now leave a review.")}>
                          Mark as completed
                        </Button>
                      )}
                      <Button variant="secondary" onClick={() => setMode({ id: b.id, kind: "cancel" })}>
                        Cancel booking
                      </Button>
                    </>
                  )}
                </div>
              )}

              {mode?.id === b.id && mode.kind === "confirm" && (
                <div className="mt-3 flex flex-wrap items-end gap-3 rounded-lg border border-stone-200 bg-stone-50 p-3">
                  <FormField label="Agreed amount (₹)" type="number" min={0} step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
                  <Button loading={busy} disabled={amount === ""} onClick={() => act(b, "confirm", { agreed_amount: Number(amount) }, "Booking confirmed.")}>
                    Confirm
                  </Button>
                  <Button variant="secondary" onClick={() => setMode(null)}>
                    Back
                  </Button>
                </div>
              )}
              {mode?.id === b.id && (mode.kind === "reject" || mode.kind === "cancel") && (
                <div className="mt-3">
                  <ReasonPrompt
                    label="Reason (shown to the customer)"
                    confirmLabel={mode.kind === "reject" ? "Decline booking" : "Cancel booking"}
                    onCancel={() => setMode(null)}
                    onConfirm={(reason) => act(b, mode.kind, { reason }, mode.kind === "reject" ? "Booking declined." : "Booking cancelled.")}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="bookings" onPage={setPage} />}
    </div>
  );
}
