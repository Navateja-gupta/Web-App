import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Spinner from "../../components/Spinner";
import { QuotationPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate, formatINR } from "../../lib/format";
import type { Enquiry, Quotation } from "../../types";

interface Row {
  quotation: Quotation;
  enquiry: Enquiry;
}

/** Side-by-side comparison of quotations, grouped by service category. */
export default function QuotationsPage() {
  const navigate = useNavigate();
  const [enquiries, setEnquiries] = useState<Enquiry[] | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setEnquiries((await api.get<Enquiry[]>("/me/quotation-requests")).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const groups = useMemo(() => {
    const rows: Row[] = (enquiries ?? []).flatMap((enquiry) =>
      enquiry.quotations.filter((q) => showAll || q.status === "sent").map((quotation) => ({ quotation, enquiry })),
    );
    const byCategory = new Map<string, Row[]>();
    for (const row of rows) {
      const key = row.quotation.vendor.category.name;
      byCategory.set(key, [...(byCategory.get(key) ?? []), row]);
    }
    for (const list of byCategory.values()) list.sort((a, b) => a.quotation.quoted_amount - b.quotation.quoted_amount);
    return [...byCategory.entries()];
  }, [enquiries, showAll]);

  async function accept(q: Quotation) {
    if (
      !window.confirm(
        `Accept ${q.vendor.business_name}'s quotation of ${formatINR(q.quoted_amount)}?\n\nThis sends a booking request. The booking is confirmed only after the vendor confirms it.`,
      )
    )
      return;
    setBusy(q.id);
    setError(null);
    try {
      await api.post(`/me/quotations/${q.id}/accept`);
      navigate("/bookings", { state: { accepted: q.vendor.business_name } });
    } catch (err) {
      setError(getErrorMessage(err));
      setBusy(null);
    }
  }

  async function reject(q: Quotation) {
    setBusy(q.id);
    setError(null);
    try {
      await api.post(`/me/quotations/${q.id}/reject`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">Compare quotations</h1>
          <p className="text-stone-600">Quotations from different vendors, cheapest first in each service.</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-stone-700">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Show past quotations
        </label>
      </div>
      {error && <Alert kind="error">{error}</Alert>}

      {!enquiries ? (
        <Spinner />
      ) : groups.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">
          No quotations to compare yet. Vendors' replies to your{" "}
          <Link to="/enquiries" className="text-maroon-700 underline">
            enquiries
          </Link>{" "}
          will appear here.
        </p>
      ) : (
        groups.map(([category, rows]) => (
          <div key={category} className="space-y-2">
            <h2 className="text-lg font-semibold">{category}</h2>
            <div className="overflow-x-auto rounded-xl border border-maroon-100 bg-white">
              <table className="min-w-full divide-y divide-stone-200 text-sm">
                <thead className="bg-stone-50 text-left text-stone-600">
                  <tr>
                    <th className="px-4 py-3 font-medium">Vendor</th>
                    <th className="px-4 py-3 font-medium">Amount</th>
                    <th className="px-4 py-3 font-medium">Included</th>
                    <th className="px-4 py-3 font-medium">Not included</th>
                    <th className="px-4 py-3 font-medium">Event / valid until</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 align-top">
                  {rows.map(({ quotation: q, enquiry }) => (
                    <tr key={q.id}>
                      <td className="px-4 py-3">
                        <Link to={`/vendors/${q.vendor.slug}`} className="font-medium text-maroon-700 hover:underline">
                          {q.vendor.business_name}
                        </Link>
                        {q.description && <p className="mt-1 max-w-xs whitespace-pre-line text-xs text-stone-600">{q.description}</p>}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-base font-semibold text-maroon-800">{formatINR(q.quoted_amount)}</td>
                      <td className="px-4 py-3">
                        <ul className="space-y-0.5">{q.inclusions.map((i) => <li key={i}>✓ {i}</li>)}</ul>
                      </td>
                      <td className="px-4 py-3">
                        <ul className="space-y-0.5 text-stone-600">{q.exclusions.map((i) => <li key={i}>✕ {i}</li>)}</ul>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {formatDate(enquiry.service_date)}
                        <br />
                        <span className="text-xs text-stone-500">{q.validity_date ? `valid until ${formatDate(q.validity_date)}` : "no expiry given"}</span>
                      </td>
                      <td className="px-4 py-3">
                        <QuotationPill status={q.status} />
                      </td>
                      <td className="space-y-1 px-4 py-3 text-right">
                        {q.status === "sent" && (
                          <>
                            <Button className="w-full px-3 py-1.5" loading={busy === q.id} onClick={() => accept(q)}>
                              Accept
                            </Button>
                            <Button variant="secondary" className="w-full px-3 py-1.5" disabled={busy === q.id} onClick={() => reject(q)}>
                              Decline
                            </Button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))
      )}
    </section>
  );
}
