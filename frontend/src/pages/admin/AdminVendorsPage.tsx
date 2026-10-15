import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Spinner from "../../components/Spinner";
import { ApprovalBadge, Badge } from "../../components/StatusBadge";
import { api, getErrorMessage } from "../../lib/api";
import { APPROVAL_LABEL, formatDate } from "../../lib/format";
import type { ApprovalStatus, Category, Page, VendorAdmin } from "../../types";

const PAGE_SIZE = 20;
const STATUSES: ("" | ApprovalStatus)[] = ["pending", "approved", "rejected", "suspended", ""];

export default function AdminVendorsPage() {
  const [params, setParams] = useSearchParams();
  // Default view is the approval queue; "all" in the URL means no status filter.
  const rawStatus = params.get("status") ?? "pending";
  const status = (rawStatus === "all" ? "" : rawStatus) as "" | ApprovalStatus;
  const categoryId = params.get("category") ?? "";
  const search = params.get("q") ?? "";
  const page = Number(params.get("page") ?? "1");

  const [searchDraft, setSearchDraft] = useState(search);
  const [categories, setCategories] = useState<Category[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [data, setData] = useState<Page<VendorAdmin> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!("page" in changes)) next.delete("page");
    setParams(next);
  };

  useEffect(() => {
    api.get<Category[]>("/admin/categories").then((r) => setCategories(r.data)).catch(() => undefined);
    api.get<Record<string, number>>("/admin/vendors/status-counts").then((r) => setCounts(r.data)).catch(() => undefined);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Page<VendorAdmin>>("/admin/vendors", {
        params: {
          approval_status: status || undefined,
          category_id: categoryId || undefined,
          search: search || undefined,
          page,
          size: PAGE_SIZE,
        },
      });
      setData(res.data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [status, categoryId, search, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function submitSearch(e: FormEvent) {
    e.preventDefault();
    update({ q: searchDraft.trim() });
  }

  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">Vendors</h1>
          <p className="text-stone-600">Review new profiles and manage listings.</p>
        </div>
        <Link to="/admin/vendors/new" className="rounded-lg bg-maroon-700 px-4 py-2 text-sm font-medium text-white hover:bg-maroon-800">
          Add vendor
        </Link>
      </div>

      <div role="tablist" className="flex flex-wrap gap-1 border-b border-stone-200">
        {STATUSES.map((s) => (
          <button
            key={s || "all"}
            role="tab"
            aria-selected={status === s}
            onClick={() => update({ status: s || "all" })}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              status === s ? "border-maroon-700 text-maroon-800" : "border-transparent text-stone-600 hover:text-maroon-700"
            }`}
          >
            {s ? APPROVAL_LABEL[s] : "All"} ({s ? counts[s] ?? 0 : total})
          </button>
        ))}
      </div>

      <form onSubmit={submitSearch} className="flex flex-wrap items-end gap-3">
        <label className="flex-1 text-sm">
          <span className="block font-medium text-stone-700">Search</span>
          <input
            className="mt-1 w-full min-w-48 rounded-lg border border-stone-300 px-3 py-2"
            placeholder="Business name, location, phone or email"
            maxLength={100}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="block font-medium text-stone-700">Category</span>
          <select className="mt-1 rounded-lg border border-stone-300 bg-white px-3 py-2" value={categoryId} onChange={(e) => update({ category: e.target.value })}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {!c.is_active && " (inactive)"}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit">Search</Button>
      </form>

      {error && <Alert kind="error">{error}</Alert>}

      {loading && !data ? (
        <Spinner />
      ) : data && data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">
          {status === "pending" && !search && !categoryId ? "No vendors are waiting for approval." : "No vendors match these filters."}
        </p>
      ) : (
        data && (
          <div className="overflow-x-auto rounded-xl border border-maroon-100 bg-white">
            <table className="min-w-full divide-y divide-stone-200 text-sm">
              <thead className="bg-stone-50 text-left text-stone-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Business</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Location</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Account</th>
                  <th className="px-4 py-3 font-medium">Added</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {data.items.map((v) => (
                  <tr key={v.id} className="hover:bg-maroon-50/40">
                    <td className="px-4 py-3">
                      <Link to={`/admin/vendors/${v.id}`} className="font-medium text-maroon-700 underline-offset-2 hover:underline">
                        {v.business_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{v.category.name}</td>
                    <td className="px-4 py-3">{v.location}</td>
                    <td className="space-x-1 px-4 py-3">
                      <ApprovalBadge status={v.approval_status} />
                      {!v.is_active && <Badge tone="grey">Inactive</Badge>}
                    </td>
                    <td className="px-4 py-3">{v.user ? v.user.email : <span className="text-stone-500">Not linked</span>}</td>
                    <td className="px-4 py-3">{formatDate(v.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-stone-600">
          <span>
            Page {data.page} of {data.pages} · {data.total} vendors
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1} onClick={() => update({ page: String(page - 1) })}>
              Previous
            </Button>
            <Button variant="secondary" disabled={page >= data.pages} onClick={() => update({ page: String(page + 1) })}>
              Next
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
