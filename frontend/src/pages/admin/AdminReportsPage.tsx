import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { Badge } from "../../components/StatusBadge";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import { REPORT_REASON_LABEL, formatDate } from "../../lib/format";
import type { CustomerContact, Page, ReportReason, VendorSummary } from "../../types";

interface ReportItem {
  id: number;
  reason: ReportReason;
  details: string | null;
  status: "open" | "resolved" | "dismissed";
  admin_notes: string | null;
  created_at: string;
  resolved_at: string | null;
  reporter: CustomerContact | null;
  vendor: VendorSummary | null;
  review_id: number | null;
}

export default function AdminReportsPage() {
  const [status, setStatus] = useState<"open" | "resolved" | "dismissed" | "">("open");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<ReportItem> | null>(null);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<ReportItem>>("/admin/reports", { params: { status: status || undefined, page, size: 20 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [status, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(r: ReportItem, outcome: "resolved" | "dismissed") {
    try {
      await api.post(`/admin/reports/${r.id}/resolve`, { status: outcome, admin_notes: notes[r.id]?.trim() || null });
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Complaints & reported content</h1>
        <p className="text-stone-600">
          Investigate, then act on the listing (suspend/edit the vendor, or hide a review) and record the outcome here.
        </p>
      </div>
      <select
        aria-label="Filter by status"
        className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm"
        value={status}
        onChange={(e) => {
          setStatus(e.target.value as typeof status);
          setPage(1);
        }}
      >
        <option value="open">Open</option>
        <option value="resolved">Resolved</option>
        <option value="dismissed">Dismissed</option>
        <option value="">All</option>
      </select>
      {error && <Alert kind="error">{error}</Alert>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">Nothing here.</p>
      ) : (
        <ul className="space-y-3">
          {data.items.map((r) => (
            <li key={r.id} className="space-y-2 rounded-xl border border-maroon-100 bg-white p-4 text-sm shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium">{REPORT_REASON_LABEL[r.reason]}</p>
                  <p className="text-stone-600">
                    {r.vendor ? (
                      <>
                        Listing:{" "}
                        <Link to={`/admin/vendors/${r.vendor.id}`} className="text-maroon-700 underline">
                          {r.vendor.business_name}
                        </Link>
                      </>
                    ) : (
                      <Link to="/admin/reviews" className="text-maroon-700 underline">
                        Review #{r.review_id}
                      </Link>
                    )}
                    {" · "}reported by {r.reporter ? `${r.reporter.full_name} (${r.reporter.email})` : "a deleted user"} on {formatDate(r.created_at)}
                  </p>
                  {r.details && <p className="mt-1 whitespace-pre-line">{r.details}</p>}
                  {r.admin_notes && <p className="mt-1 text-stone-600">Admin notes: {r.admin_notes}</p>}
                </div>
                <Badge tone={r.status === "open" ? "amber" : r.status === "resolved" ? "green" : "grey"}>{r.status}</Badge>
              </div>
              {r.status === "open" && (
                <>
                  <TextArea label="Notes (internal)" rows={2} maxLength={2000} value={notes[r.id] ?? ""} onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} />
                  <div className="flex gap-2">
                    <Button className="px-3 py-1.5" onClick={() => resolve(r, "resolved")}>
                      Mark resolved
                    </Button>
                    <Button variant="secondary" className="px-3 py-1.5" onClick={() => resolve(r, "dismissed")}>
                      Dismiss
                    </Button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="reports" onPage={setPage} />}
    </section>
  );
}
