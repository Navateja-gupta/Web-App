import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Pagination from "../../components/Pagination";
import ReasonPrompt from "../../components/ReasonPrompt";
import Spinner from "../../components/Spinner";
import { BookingPill } from "../../components/StatusPill";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate, formatINR } from "../../lib/format";
import type { Booking, Page } from "../../types";

function ReviewForm({ booking, onDone }: { booking: Booking; onDone: () => void }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!rating) return setError("Choose a rating.");
    setSaving(true);
    setError(null);
    try {
      await api.post(`/me/bookings/${booking.id}/review`, { rating, comment: comment.trim() || null });
      onDone();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-3 space-y-3 rounded-lg border border-stone-200 bg-stone-50 p-3">
      {error && <Alert kind="error">{error}</Alert>}
      <fieldset>
        <legend className="text-sm font-medium text-stone-700">Your rating for {booking.vendor.business_name}</legend>
        <div className="mt-1 flex gap-1" role="radiogroup">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={rating === n}
              aria-label={`${n} star${n > 1 ? "s" : ""}`}
              onClick={() => setRating(n)}
              className={`text-2xl ${n <= rating ? "text-gold-500" : "text-stone-300"}`}
            >
              ★
            </button>
          ))}
        </div>
      </fieldset>
      <TextArea label="Comment (optional)" rows={3} maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)} />
      <Button type="submit" loading={saving}>
        Submit review
      </Button>
    </form>
  );
}

export default function BookingsPage() {
  const location = useLocation();
  const accepted = (location.state as { accepted?: string } | null)?.accepted;
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Booking> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<number | null>(null);
  const [reviewing, setReviewing] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<Booking>>("/me/bookings", { params: { page, size: 20 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Bookings</h1>
        <p className="text-stone-600">A booking is confirmed only after the vendor confirms it.</p>
      </div>
      {accepted && <Alert kind="success">Booking request sent to {accepted}. You will see it here once they confirm.</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      {error && <Alert kind="error">{error}</Alert>}

      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">
          No bookings yet. Accept a quotation on the{" "}
          <Link to="/quotations" className="text-maroon-700 underline">
            comparison page
          </Link>{" "}
          to send a booking request.
        </p>
      ) : (
        <ul className="space-y-4">
          {data.items.map((b) => (
            <li key={b.id} className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link to={`/vendors/${b.vendor.slug}`} className="font-semibold text-maroon-800 hover:underline">
                    {b.vendor.business_name}
                  </Link>
                  <p className="text-sm text-stone-600">
                    {b.vendor.category.name} · {formatDate(b.event_date)}
                    {b.event_location ? ` · ${b.event_location}` : ""}
                    {b.package ? ` · ${b.package.name}` : ""}
                  </p>
                  <p className="mt-1 text-sm">
                    {b.agreed_amount !== null ? <>Agreed amount: <strong>{formatINR(b.agreed_amount)}</strong></> : "Amount to be confirmed by vendor"}
                    {" · "}Vendor phone:{" "}
                    <a href={`tel:${b.vendor.contact_phone}`} className="text-maroon-700 underline">
                      {b.vendor.contact_phone}
                    </a>
                  </p>
                  {b.cancellation_reason && <p className="mt-1 text-sm text-stone-600">Reason: {b.cancellation_reason}</p>}
                </div>
                <BookingPill status={b.booking_status} />
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {(b.booking_status === "requested" || b.booking_status === "confirmed") && cancelling !== b.id && (
                  <Button variant="secondary" className="px-3 py-1.5" onClick={() => setCancelling(b.id)}>
                    Cancel booking
                  </Button>
                )}
                {b.booking_status === "completed" && !b.has_review && reviewing !== b.id && (
                  <Button className="px-3 py-1.5" onClick={() => setReviewing(b.id)}>
                    Write a review
                  </Button>
                )}
                {b.has_review && <span className="text-sm text-stone-500">Thank you for your review.</span>}
              </div>

              {cancelling === b.id && (
                <div className="mt-3">
                  <ReasonPrompt
                    label="Why are you cancelling?"
                    confirmLabel="Cancel booking"
                    onCancel={() => setCancelling(null)}
                    onConfirm={async (reason) => {
                      try {
                        await api.post(`/me/bookings/${b.id}/cancel`, { reason });
                        setCancelling(null);
                        setNotice("Booking cancelled.");
                        await load();
                      } catch (err) {
                        setError(getErrorMessage(err));
                      }
                    }}
                  />
                </div>
              )}
              {reviewing === b.id && (
                <ReviewForm
                  booking={b}
                  onDone={() => {
                    setReviewing(null);
                    setNotice("Review published. Thank you!");
                    void load();
                  }}
                />
              )}
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="bookings" onPage={setPage} />}
    </section>
  );
}
