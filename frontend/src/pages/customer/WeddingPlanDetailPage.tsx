import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import SelectField from "../../components/SelectField";
import Spinner from "../../components/Spinner";
import StatCard from "../../components/StatCard";
import { PlanItemPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { PLAN_ITEM_LABEL, formatDate, formatINR } from "../../lib/format";
import type { Category, PlanItem, PlanItemStatus, WeddingPlan } from "../../types";

const STATUS_OPTIONS = Object.entries(PLAN_ITEM_LABEL).map(([value, label]) => ({ value, label }));

interface ItemDraft {
  description: string;
  category_id: string;
  estimated_cost: string;
  actual_cost: string;
  status: PlanItemStatus;
}

const emptyDraft: ItemDraft = { description: "", category_id: "", estimated_cost: "", actual_cost: "", status: "planned" };

function toBody(d: ItemDraft) {
  return {
    description: d.description.trim(),
    category_id: d.category_id ? Number(d.category_id) : null,
    estimated_cost: d.estimated_cost ? Number(d.estimated_cost) : 0,
    actual_cost: d.actual_cost === "" ? null : Number(d.actual_cost),
    status: d.status,
  };
}

function ItemFields({ draft, setDraft, categories }: { draft: ItemDraft; setDraft: (d: ItemDraft) => void; categories: Category[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-5">
      <FormField label="Expense" required className="sm:col-span-2" maxLength={255} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
      <SelectField
        label="Service"
        value={draft.category_id}
        onChange={(e) => setDraft({ ...draft, category_id: e.target.value })}
        placeholder="—"
        options={categories.map((c) => ({ value: String(c.id), label: c.name }))}
      />
      <FormField label="Estimated (₹)" type="number" min={0} value={draft.estimated_cost} onChange={(e) => setDraft({ ...draft, estimated_cost: e.target.value })} />
      <FormField label="Actual (₹)" type="number" min={0} value={draft.actual_cost} onChange={(e) => setDraft({ ...draft, actual_cost: e.target.value })} />
      <SelectField label="Status" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value as PlanItemStatus })} options={STATUS_OPTIONS} />
    </div>
  );
}

export default function WeddingPlanDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<WeddingPlan | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [draft, setDraft] = useState<ItemDraft>(emptyDraft);
  const [editing, setEditing] = useState<{ id: number; draft: ItemDraft } | null>(null);
  const [budgetDraft, setBudgetDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const base = `/me/wedding-plans/${id}`;

  const load = useCallback(async () => {
    try {
      const res = await api.get<WeddingPlan>(base);
      setPlan(res.data);
      setBudgetDraft(res.data.estimated_budget !== null ? String(res.data.estimated_budget) : "");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [base]);

  useEffect(() => {
    void load();
    api.get<Category[]>("/categories").then((r) => setCategories(r.data)).catch(() => undefined);
  }, [load]);

  async function run(action: () => Promise<{ data: WeddingPlan }>) {
    setBusy(true);
    setError(null);
    try {
      setPlan((await action()).data);
      return true;
    } catch (err) {
      setError(getErrorMessage(err));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function addItem(e: FormEvent) {
    e.preventDefault();
    if (draft.description.trim().length < 2) return setError("Describe the expense.");
    if (await run(() => api.post<WeddingPlan>(`${base}/items`, toBody(draft)))) setDraft(emptyDraft);
  }

  async function saveEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    if (await run(() => api.patch<WeddingPlan>(`${base}/items/${editing.id}`, toBody(editing.draft)))) setEditing(null);
  }

  async function deletePlan() {
    if (!plan || !window.confirm(`Delete “${plan.event_name}” and all its budget lines? Bookings and enquiries are kept.`)) return;
    try {
      await api.delete(base);
      navigate("/plans");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  if (!plan) return error ? <Alert kind="error">{error}</Alert> : <Spinner />;
  const b = plan.budget;

  return (
    <section className="space-y-6">
      <Link to="/plans" className="text-sm text-maroon-700 underline">
        ← All events
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">{plan.event_name}</h1>
          <p className="text-stone-600">
            {plan.event_date ? formatDate(plan.event_date) : "Date not set"}
            {plan.location ? ` · ${plan.location}` : ""}
            {plan.guest_count ? ` · ${plan.guest_count} guests` : ""}
          </p>
        </div>
        <Button variant="danger" onClick={deletePlan}>
          Delete event
        </Button>
      </div>
      {error && <Alert kind="error">{error}</Alert>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total budget" value={b.estimated_budget !== null ? formatINR(b.estimated_budget) : "Not set"} />
        <StatCard label="Committed" value={formatINR(b.committed)} hint="Actual cost where known, otherwise estimate" />
        <StatCard label="Paid / actual so far" value={formatINR(b.total_actual)} />
        <StatCard
          label={b.over_budget ? "Over budget by" : "Remaining"}
          value={b.remaining !== null ? <span className={b.over_budget ? "text-red-700" : ""}>{formatINR(Math.abs(b.remaining))}</span> : "—"}
        />
      </div>

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void run(() => api.patch<WeddingPlan>(base, { estimated_budget: budgetDraft === "" ? null : Number(budgetDraft) }));
        }}
      >
        <FormField label="Update total budget (₹)" type="number" min={0} value={budgetDraft} onChange={(e) => setBudgetDraft(e.target.value)} />
        <Button type="submit" variant="secondary" loading={busy}>
          Save budget
        </Button>
      </form>

      <div className="overflow-x-auto rounded-xl border border-maroon-100 bg-white">
        <table className="min-w-full divide-y divide-stone-200 text-sm">
          <thead className="bg-stone-50 text-left text-stone-600">
            <tr>
              <th className="px-4 py-3 font-medium">Expense</th>
              <th className="px-4 py-3 font-medium">Service / vendor</th>
              <th className="px-4 py-3 text-right font-medium">Estimated</th>
              <th className="px-4 py-3 text-right font-medium">Actual</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {plan.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-stone-600">
                  No expenses yet. Add your first one below, even before choosing a vendor.
                </td>
              </tr>
            )}
            {plan.items.map((item: PlanItem) =>
              editing?.id === item.id ? (
                <tr key={item.id}>
                  <td colSpan={6} className="px-4 py-3">
                    <form onSubmit={saveEdit} className="space-y-3">
                      <ItemFields draft={editing.draft} setDraft={(d) => setEditing({ id: item.id, draft: d })} categories={categories} />
                      <div className="flex gap-2">
                        <Button type="submit" loading={busy}>
                          Save
                        </Button>
                        <Button type="button" variant="secondary" onClick={() => setEditing(null)}>
                          Cancel
                        </Button>
                      </div>
                    </form>
                  </td>
                </tr>
              ) : (
                <tr key={item.id} className={item.status === "cancelled" ? "text-stone-400 line-through" : ""}>
                  <td className="px-4 py-3 font-medium">{item.description}</td>
                  <td className="px-4 py-3">
                    {item.category?.name ?? "—"}
                    {item.vendor && (
                      <>
                        {" · "}
                        <Link to={`/vendors/${item.vendor.slug}`} className="text-maroon-700 underline">
                          {item.vendor.business_name}
                        </Link>
                      </>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">{formatINR(item.estimated_cost)}</td>
                  <td className="px-4 py-3 text-right">{item.actual_cost !== null ? formatINR(item.actual_cost) : "—"}</td>
                  <td className="px-4 py-3 no-underline">
                    <PlanItemPill status={item.status} />
                  </td>
                  <td className="space-x-1 whitespace-nowrap px-4 py-3 text-right no-underline">
                    <Button
                      variant="secondary"
                      className="px-2 py-1"
                      onClick={() =>
                        setEditing({
                          id: item.id,
                          draft: {
                            description: item.description,
                            category_id: item.category ? String(item.category.id) : "",
                            estimated_cost: String(item.estimated_cost),
                            actual_cost: item.actual_cost !== null ? String(item.actual_cost) : "",
                            status: item.status,
                          },
                        })
                      }
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      className="px-2 py-1"
                      onClick={() => window.confirm(`Remove “${item.description}”?`) && run(() => api.delete<WeddingPlan>(`${base}/items/${item.id}`))}
                    >
                      Remove
                    </Button>
                  </td>
                </tr>
              ),
            )}
          </tbody>
          {plan.items.length > 0 && (
            <tfoot className="bg-stone-50 font-medium">
              <tr>
                <td className="px-4 py-3" colSpan={2}>
                  Total (excluding cancelled)
                </td>
                <td className="px-4 py-3 text-right">{formatINR(b.total_estimated)}</td>
                <td className="px-4 py-3 text-right">{formatINR(b.total_actual)}</td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <form onSubmit={addItem} className="space-y-3 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm" noValidate>
        <h2 className="font-semibold">Add expense</h2>
        <ItemFields draft={draft} setDraft={setDraft} categories={categories} />
        <Button type="submit" loading={busy}>
          Add expense
        </Button>
      </form>
    </section>
  );
}
