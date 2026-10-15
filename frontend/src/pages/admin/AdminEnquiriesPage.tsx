import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "../../components/Alert";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { EnquiryPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { ENQUIRY_LABEL, formatDate, formatINR } from "../../lib/format";
import type { Enquiry, EnquiryStatus, Page } from "../../types";

export default function AdminEnquiriesPage() {
  const [status, setStatus] = useState<"" | EnquiryStatus>("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Enquiry> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Page<Enquiry>>("/admin/quotation-requests", { params: { status: status || undefined, page, size: 20 } })
      .then((r) => setData(r.data))
      .catch((err) => setError(getErrorMessage(err)));
  }, [status, page]);

  return (
    <section className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Enquiries</h1>
        <p className="text-stone-600">All quotation requests between customers and vendors.</p>
      </div>
      <select
        aria-label="Filter by status"
        className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm"
        value={status}
        onChange={(e) => {
          setStatus(e.target.value as "" | EnquiryStatus);
          setPage(1);
        }}
      >
        <option value="">All statuses</option>
        {Object.entries(ENQUIRY_LABEL).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
      {error && <Alert kind="error">{error}</Alert>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No enquiries.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-maroon-100 bg-white">
          <table className="min-w-full divide-y divide-stone-200 text-sm">
            <thead className="bg-stone-50 text-left text-stone-600">
              <tr>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium">Vendor</th>
                <th className="px-4 py-3 font-medium">Event</th>
                <th className="px-4 py-3 font-medium">Latest quote</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Received</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {data.items.map((e) => {
                const latest = e.quotations[e.quotations.length - 1];
                return (
                  <tr key={e.id}>
                    <td className="px-4 py-3">
                      {e.customer?.full_name}
                      <br />
                      <span className="text-xs text-stone-500">{e.customer?.email}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/admin/vendors/${e.vendor.id}`} className="text-maroon-700 underline">
                        {e.vendor.business_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      {formatDate(e.service_date)}
                      <br />
                      <span className="text-xs text-stone-500">{e.event_location}</span>
                    </td>
                    <td className="px-4 py-3">{latest ? formatINR(latest.quoted_amount) : "—"}</td>
                    <td className="px-4 py-3">
                      <EnquiryPill status={e.status} />
                    </td>
                    <td className="px-4 py-3">{formatDate(e.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="enquiries" onPage={setPage} />}
    </section>
  );
}
