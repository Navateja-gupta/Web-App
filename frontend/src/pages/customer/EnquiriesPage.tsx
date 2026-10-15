import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Spinner from "../../components/Spinner";
import { EnquiryPill, QuotationPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate, formatINR } from "../../lib/format";
import type { Enquiry } from "../../types";

export default function EnquiriesPage() {
  const location = useLocation();
  const sent = (location.state as { sent?: number } | null)?.sent;
  const [items, setItems] = useState<Enquiry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems((await api.get<Enquiry[]>("/me/quotation-requests")).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function cancel(id: number) {
    if (!window.confirm("Cancel this enquiry? The vendor will no longer be able to send a quotation.")) return;
    setError(null);
    try {
      await api.post(`/me/quotation-requests/${id}/cancel`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">Enquiries</h1>
          <p className="text-stone-600">Requirements you have sent to vendors and their replies.</p>
        </div>
        <Link to="/request-quote" className="rounded-lg bg-maroon-700 px-4 py-2 text-sm font-medium text-white hover:bg-maroon-800">
          New enquiry
        </Link>
      </div>
      {sent && <Alert kind="success">Your enquiry was sent to {sent} {sent === 1 ? "vendor" : "vendors"}.</Alert>}
      {error && <Alert kind="error">{error}</Alert>}

      {!items ? (
        <Spinner />
      ) : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">
          No enquiries yet. Open a vendor's page and choose “Request a quotation”.
        </p>
      ) : (
        <ul className="space-y-4">
          {items.map((e) => (
            <li key={e.id} className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link to={`/vendors/${e.vendor.slug}`} className="font-semibold text-maroon-800 hover:underline">
                    {e.vendor.business_name}
                  </Link>
                  <p className="text-sm text-stone-600">
                    {e.vendor.category.name} · Event on {formatDate(e.service_date)} at {e.event_location}
                    {e.guest_count ? ` · ${e.guest_count} guests` : ""}
                    {e.budget !== null ? ` · budget ${formatINR(e.budget)}` : ""}
                  </p>
                </div>
                <EnquiryPill status={e.status} />
              </div>
              <p className="mt-2 whitespace-pre-line text-sm text-stone-700">{e.requirements}</p>
              {e.vendor_response && <Alert kind="info">Vendor replied: {e.vendor_response}</Alert>}

              {e.quotations.length > 0 && (
                <ul className="mt-3 space-y-1 border-t border-stone-100 pt-3 text-sm">
                  {e.quotations.map((q) => (
                    <li key={q.id} className="flex flex-wrap items-center justify-between gap-2">
                      <span>
                        Quotation: <strong>{formatINR(q.quoted_amount)}</strong>
                        {q.validity_date && ` · valid until ${formatDate(q.validity_date)}`}
                      </span>
                      <QuotationPill status={q.status} />
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-3 flex flex-wrap gap-2">
                {e.quotations.some((q) => q.status === "sent") && (
                  <Link to="/quotations" className="rounded-lg bg-maroon-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-maroon-800">
                    Compare and decide
                  </Link>
                )}
                {(e.status === "pending" || e.status === "quoted") && (
                  <Button variant="secondary" className="px-3 py-1.5" onClick={() => cancel(e.id)}>
                    Cancel enquiry
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
