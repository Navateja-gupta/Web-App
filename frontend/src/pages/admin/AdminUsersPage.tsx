import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../../auth/AuthContext";
import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Spinner from "../../components/Spinner";
import { api, getErrorMessage } from "../../lib/api";
import type { Page, Role, User } from "../../types";

const PAGE_SIZE = 20;

interface Filters {
  search: string;
  role: "" | Role;
  status: "" | "active" | "inactive";
}

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const [draft, setDraft] = useState<Filters>({ search: "", role: "", status: "" });
  const [filters, setFilters] = useState<Filters>(draft);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<User> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Page<User>>("/admin/users", {
        params: {
          page,
          size: PAGE_SIZE,
          search: filters.search || undefined,
          role: filters.role || undefined,
          is_active: filters.status === "" ? undefined : filters.status === "active",
        },
      });
      setData(res.data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    void load();
  }, [load]);

  function applyFilters(e: FormEvent) {
    e.preventDefault();
    setPage(1);
    setFilters(draft);
  }

  async function toggleActive(target: User) {
    const action = target.is_active ? "deactivate" : "activate";
    if (!window.confirm(`Are you sure you want to ${action} ${target.full_name}?`)) return;
    setBusyId(target.id);
    setNotice(null);
    setError(null);
    try {
      await api.patch<User>(`/admin/users/${target.id}`, { is_active: !target.is_active });
      setNotice(`${target.full_name} has been ${action}d.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Users</h1>
        <p className="mt-1 text-stone-600">Customers, vendors and administrators registered on the platform.</p>
      </div>

      <form onSubmit={applyFilters} className="flex flex-wrap items-end gap-3 rounded-xl border border-maroon-100 bg-white p-4">
        <label className="flex-1 text-sm">
          <span className="block font-medium text-stone-700">Search</span>
          <input
            className="mt-1 w-full min-w-48 rounded-lg border border-stone-300 px-3 py-2"
            placeholder="Name, email or phone"
            value={draft.search}
            maxLength={100}
            onChange={(e) => setDraft({ ...draft, search: e.target.value })}
          />
        </label>
        <label className="text-sm">
          <span className="block font-medium text-stone-700">Role</span>
          <select
            className="mt-1 rounded-lg border border-stone-300 px-3 py-2"
            value={draft.role}
            onChange={(e) => setDraft({ ...draft, role: e.target.value as Filters["role"] })}
          >
            <option value="">All roles</option>
            <option value="customer">Customer</option>
            <option value="vendor">Vendor</option>
            <option value="admin">Administrator</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="block font-medium text-stone-700">Status</span>
          <select
            className="mt-1 rounded-lg border border-stone-300 px-3 py-2"
            value={draft.status}
            onChange={(e) => setDraft({ ...draft, status: e.target.value as Filters["status"] })}
          >
            <option value="">Any status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
        <Button type="submit">Apply</Button>
      </form>

      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      {loading && !data ? (
        <Spinner />
      ) : data && data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">
          No users match these filters.
        </p>
      ) : (
        data && (
          <div className="overflow-x-auto rounded-xl border border-maroon-100 bg-white">
            <table className="min-w-full divide-y divide-stone-200 text-sm">
              <thead className="bg-stone-50 text-left text-stone-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Phone</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Joined</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {data.items.map((u) => (
                  <tr key={u.id}>
                    <td className="px-4 py-3 font-medium">{u.full_name}</td>
                    <td className="px-4 py-3">{u.email}</td>
                    <td className="px-4 py-3">{u.phone ?? "—"}</td>
                    <td className="px-4 py-3 capitalize">{u.role}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          u.is_active ? "bg-green-100 text-green-800" : "bg-stone-200 text-stone-700"
                        }`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3">{new Date(u.created_at).toLocaleDateString("en-IN")}</td>
                    <td className="px-4 py-3 text-right">
                      {u.id !== me?.id && (
                        <Button
                          variant={u.is_active ? "danger" : "secondary"}
                          loading={busyId === u.id}
                          onClick={() => toggleActive(u)}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </Button>
                      )}
                    </td>
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
            Page {data.page} of {data.pages} · {data.total} users
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button variant="secondary" disabled={page >= data.pages || loading} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
