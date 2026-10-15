import { useCallback, useEffect, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import Spinner from "../../components/Spinner";
import { Badge } from "../../components/StatusBadge";
import { api, getErrorMessage } from "../../lib/api";
import type { Category } from "../../types";

interface Draft {
  name: string;
  icon: string;
  description: string;
  display_order: string;
}

const emptyDraft: Draft = { name: "", icon: "", description: "", display_order: "0" };

function toBody(d: Draft) {
  return {
    name: d.name.trim(),
    icon: d.icon.trim() || null,
    description: d.description.trim() || null,
    display_order: Number(d.display_order) || 0,
  };
}

function CategoryFields({ draft, setDraft }: { draft: Draft; setDraft: (d: Draft) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr]">
      <FormField label="Name" required maxLength={80} value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
      <FormField label="Icon" maxLength={10} hint="Optional emoji" value={draft.icon} onChange={(e) => setDraft({ ...draft, icon: e.target.value })} />
      <FormField
        label="Display order"
        type="number"
        min={0}
        value={draft.display_order}
        onChange={(e) => setDraft({ ...draft, display_order: e.target.value })}
      />
      <FormField
        label="Description"
        className="sm:col-span-3"
        maxLength={1000}
        value={draft.description}
        onChange={(e) => setDraft({ ...draft, description: e.target.value })}
      />
    </div>
  );
}

export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [editing, setEditing] = useState<{ id: number; draft: Draft } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setCategories((await api.get<Category[]>("/admin/categories")).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await load();
      return true;
    } catch (err) {
      setError(getErrorMessage(err));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    if (draft.name.trim().length < 2) return setError("Enter a category name.");
    if (await run(() => api.post("/admin/categories", toBody(draft)), `Category “${draft.name.trim()}” created.`)) setDraft(emptyDraft);
  }

  async function saveEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    if (await run(() => api.patch(`/admin/categories/${editing.id}`, toBody(editing.draft)), "Category updated.")) setEditing(null);
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Service categories</h1>
        <p className="text-stone-600">Add categories such as Mehendi Artists or Wedding Priests at any time. No code changes needed.</p>
      </div>

      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <form onSubmit={create} className="space-y-3 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
        <h2 className="font-semibold">New category</h2>
        <CategoryFields draft={draft} setDraft={setDraft} />
        <Button type="submit" loading={busy}>
          Create category
        </Button>
      </form>

      {!categories ? (
        <Spinner />
      ) : categories.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No categories yet.</p>
      ) : (
        <ul className="space-y-3">
          {categories.map((c) =>
            editing?.id === c.id ? (
              <li key={c.id}>
                <form onSubmit={saveEdit} className="space-y-3 rounded-xl border border-maroon-200 bg-white p-5">
                  <CategoryFields draft={editing.draft} setDraft={(d) => setEditing({ id: c.id, draft: d })} />
                  <div className="flex gap-2">
                    <Button type="submit" loading={busy}>
                      Save
                    </Button>
                    <Button type="button" variant="secondary" onClick={() => setEditing(null)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </li>
            ) : (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white p-4">
                <div>
                  <p className="font-medium">
                    {c.icon && <span className="mr-2">{c.icon}</span>}
                    {c.name} {!c.is_active && <Badge tone="grey">Inactive</Badge>}
                  </p>
                  <p className="text-xs text-stone-500">
                    /{c.slug} · {c.vendor_count} live {c.vendor_count === 1 ? "vendor" : "vendors"} · order {c.display_order}
                  </p>
                  {c.description && <p className="mt-1 text-sm text-stone-600">{c.description}</p>}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    onClick={() =>
                      setEditing({
                        id: c.id,
                        draft: { name: c.name, icon: c.icon ?? "", description: c.description ?? "", display_order: String(c.display_order) },
                      })
                    }
                  >
                    Edit
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      run(
                        () => api.patch(`/admin/categories/${c.id}`, { is_active: !c.is_active }),
                        c.is_active ? `“${c.name}” deactivated. Its vendors are hidden from customers.` : `“${c.name}” activated.`,
                      )
                    }
                  >
                    {c.is_active ? "Deactivate" : "Activate"}
                  </Button>
                  <Button
                    variant="danger"
                    disabled={busy}
                    onClick={() =>
                      window.confirm(`Delete “${c.name}”? This only works if no vendor uses it.`) &&
                      run(() => api.delete(`/admin/categories/${c.id}`), `“${c.name}” deleted.`)
                    }
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ),
          )}
        </ul>
      )}
    </section>
  );
}
