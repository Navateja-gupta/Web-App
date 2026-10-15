import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import Alert from "../../components/Alert";
import Button from "../../components/Button";
import SelectField from "../../components/SelectField";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import { REPORT_REASON_LABEL, formatDate } from "../../lib/format";
import type { ReportReason, VendorReviews } from "../../types";

/** Customers go to the enquiry form; visitors are asked to log in; vendors/admins see nothing. */
export function RequestQuoteButton({ slug }: { slug: string }) {
  const { user } = useAuth();
  const location = useLocation();
  const className = "inline-flex justify-center rounded-lg bg-maroon-700 px-4 py-2 text-sm font-medium text-white hover:bg-maroon-800";
  if (!user) {
    return (
      <Link to={`/login?next=${encodeURIComponent(location.pathname)}`} className={className}>
        Log in to request a quotation
      </Link>
    );
  }
  if (user.role !== "customer") return null;
  return (
    <Link to={`/request-quote?vendor=${encodeURIComponent(slug)}`} className={className}>
      Request a quotation
    </Link>
  );
}

export function Stars({ value }: { value: number }) {
  const full = Math.round(value);
  return (
    <span aria-label={`${value.toFixed(1)} out of 5`}>
      <span className="text-gold-500">{"★".repeat(full)}</span>
      <span className="text-stone-300">{"★".repeat(5 - full)}</span>
    </span>
  );
}

export function ReviewsSection({ slug }: { slug: string }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<VendorReviews | null>(null);

  useEffect(() => {
    api
      .get<VendorReviews>(`/vendors/${encodeURIComponent(slug)}/reviews`, { params: { page, size: 10 } })
      .then((r) => setData(r.data))
      .catch(() => setData({ average: null, count: 0, items: [], page: 1, pages: 0 }));
  }, [slug, page]);

  if (!data) return null;
  return (
    <section>
      <h2 className="mb-3 text-xl font-semibold">Reviews</h2>
      {data.count === 0 || data.average === null ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-6 text-stone-600">
          No reviews yet. Reviews can only be written by customers after a completed booking.
        </p>
      ) : (
        <>
          <p className="mb-3 text-stone-700">
            <Stars value={data.average} /> <strong>{data.average.toFixed(1)}</strong> out of 5 from {data.count}{" "}
            {data.count === 1 ? "verified booking" : "verified bookings"}
          </p>
          <ul className="space-y-3">
            {data.items.map((r) => (
              <li key={r.id} className="rounded-xl border border-maroon-100 bg-white p-4">
                <p className="text-sm">
                  <Stars value={r.rating} /> <span className="font-medium">{r.reviewer_name}</span>{" "}
                  <span className="text-stone-500">· {formatDate(r.created_at)}</span>
                </p>
                {r.comment && <p className="mt-1 whitespace-pre-line text-stone-700">{r.comment}</p>}
              </li>
            ))}
          </ul>
          {data.pages > 1 && (
            <div className="mt-3 flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Newer
              </Button>
              <Button variant="secondary" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
                Older
              </Button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export function ReportListing({ vendorId }: { vendorId: number }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason>("wrong_information");
  const [details, setDetails] = useState("");
  const [result, setResult] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  if (!user || user.role === "admin") return null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/reports", { vendor_id: vendorId, reason, details: details.trim() || null });
      setResult({ kind: "success", text: "Thank you. Our team will review this listing." });
      setOpen(false);
    } catch (err) {
      setResult({ kind: "error", text: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="text-sm">
      {result && <Alert kind={result.kind}>{result.text}</Alert>}
      {!open ? (
        <button type="button" onClick={() => setOpen(true)} className="text-stone-500 underline hover:text-maroon-700">
          Report this listing
        </button>
      ) : (
        <form onSubmit={submit} className="space-y-3 rounded-xl border border-stone-200 bg-white p-4">
          <SelectField
            label="What is wrong?"
            value={reason}
            onChange={(e) => setReason(e.target.value as ReportReason)}
            options={Object.entries(REPORT_REASON_LABEL).map(([value, label]) => ({ value, label }))}
          />
          <TextArea label="Details" rows={3} maxLength={2000} value={details} onChange={(e) => setDetails(e.target.value)} />
          <div className="flex gap-2">
            <Button type="submit" loading={saving}>
              Send report
            </Button>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
