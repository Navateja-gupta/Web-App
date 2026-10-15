import { useEffect, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { api, getErrorMessage } from "../../lib/api";
import type { Page } from "../../types";

interface AuditEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: Record<string, unknown>;
  created_at: string;
  actor: { id: number; full_name: string; email: string } | null;
}

const ENTITY_TYPES = ["", "vendor", "category", "booking", "quotation", "quotation_request", "package", "portfolio", "review", "report", "user"];

export default function AdminAuditLogPage() {
  const [filters, setFilters] = useState({ action: "", entity_type: "" });
  const [draft, setDraft] = useState(filters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<AuditEntry> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Page<AuditEntry>>("/admin/audit-logs", {
        params: { action: filters.action || undefined, entity_type: filters.entity_type || undefined, page, size: 50 },
      })
      .then((r) => setData(r.data))
      .catch((err) => setError(getErrorMessage(err)));
  }, [filters, page]);

  function apply(e: FormEvent) {
    e.preventDefault();
    setPage(1);
    setFilters({ action: draft.action.trim(), entity_type: draft.entity_type });
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Audit log</h1>
        <p className="text-stone-600">Who did what, and when. Passwords and tokens are never recorded.</p>
      </div>
      <form onSubmit={apply} className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="block font-medium text-stone-700">Action starts with</span>
          <input
            className="mt-1 rounded-lg border border-stone-300 px-3 py-2"
            placeholder="e.g. vendor. or booking.confirmed"
            maxLength={80}
            value={draft.action}
            onChange={(e) => setDraft({ ...draft, action: e.target.value })}
          />
        </label>
        <label className="text-sm">
          <span className="block font-medium text-stone-700">Record type</span>
          <select className="mt-1 rounded-lg border border-stone-300 bg-white px-3 py-2" value={draft.entity_type} onChange={(e) => setDraft({ ...draft, entity_type: e.target.value })}>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t || "Any"}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit">Filter</Button>
      </form>
      {error && <Alert kind="error">{error}</Alert>}
      {!data ? (
        <Spinner />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-maroon-100 bg-white">
          <table className="min-w-full divide-y divide-stone-200 text-sm">
            <thead className="bg-stone-50 text-left text-stone-600">
              <tr>
                <th className="px-4 py-3 font-medium">When</th>
                <th className="px-4 py-3 font-medium">Who</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Record</th>
                <th className="px-4 py-3 font-medium">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 align-top">
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-stone-600">
                    No entries.
                  </td>
                </tr>
              )}
              {data.items.map((a) => (
                <tr key={a.id}>
                  <td className="whitespace-nowrap px-4 py-2">{new Date(a.created_at).toLocaleString("en-IN")}</td>
                  <td className="px-4 py-2">{a.actor ? a.actor.full_name : <span className="text-stone-500">System</span>}</td>
                  <td className="px-4 py-2 font-mono text-xs">{a.action}</td>
                  <td className="px-4 py-2">
                    {a.entity_type}
                    {a.entity_id !== null && ` #${a.entity_id}`}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-stone-600">{Object.keys(a.details).length ? JSON.stringify(a.details) : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="entries" onPage={setPage} />}
    </section>
  );
}
