import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import Spinner from "../../components/Spinner";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate, formatINR } from "../../lib/format";
import type { WeddingPlan, WeddingPlanSummary } from "../../types";

export default function WeddingPlansPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<WeddingPlanSummary[] | null>(null);
  const [form, setForm] = useState({ event_name: "", event_date: "", location: "", estimated_budget: "", guest_count: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setPlans((await api.get<WeddingPlanSummary[]>("/me/wedding-plans")).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [field]: e.target.value }));

  async function create(e: FormEvent) {
    e.preventDefault();
    if (form.event_name.trim().length < 2) return setError("Give the event a name, e.g. Wedding or Reception.");
    setSaving(true);
    setError(null);
    try {
      const plan = (
        await api.post<WeddingPlan>("/me/wedding-plans", {
          event_name: form.event_name.trim(),
          event_date: form.event_date || null,
          location: form.location.trim() || null,
          estimated_budget: form.estimated_budget ? Number(form.estimated_budget) : null,
          guest_count: form.guest_count ? Number(form.guest_count) : null,
        })
      ).data;
      navigate(`/plans/${plan.id}`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Wedding plan & budget</h1>
        <p className="text-stone-600">Create one plan per function (engagement, haldi, wedding, reception) and track every expense.</p>
      </div>
      {error && <Alert kind="error">{error}</Alert>}

      {!plans ? (
        <Spinner />
      ) : (
        plans.length > 0 && (
          <ul className="grid gap-4 sm:grid-cols-2">
            {plans.map((p) => (
              <li key={p.id}>
                <Link to={`/plans/${p.id}`} className="block rounded-xl border border-maroon-100 bg-white p-5 shadow-sm transition hover:border-maroon-300">
                  <p className="text-lg font-semibold text-maroon-800">{p.event_name}</p>
                  <p className="text-sm text-stone-600">
                    {p.event_date ? formatDate(p.event_date) : "Date not set"}
                    {p.location ? ` · ${p.location}` : ""}
                  </p>
                  <p className="mt-2 text-sm">
                    Committed <strong>{formatINR(p.budget.committed)}</strong>
                    {p.estimated_budget !== null && <> of {formatINR(p.estimated_budget)}</>}
                  </p>
                  {p.budget.over_budget && <p className="text-sm font-medium text-red-700">Over budget</p>}
                </Link>
              </li>
            ))}
          </ul>
        )
      )}

      <form onSubmit={create} className="space-y-4 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm" noValidate>
        <h2 className="font-semibold">Add an event</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Event name" required maxLength={150} value={form.event_name} onChange={set("event_name")} placeholder="Wedding" />
          <FormField label="Date" type="date" value={form.event_date} onChange={set("event_date")} />
          <FormField label="Location" maxLength={255} value={form.location} onChange={set("location")} />
          <FormField label="Total budget (₹)" type="number" min={0} value={form.estimated_budget} onChange={set("estimated_budget")} />
          <FormField label="Guests" type="number" min={1} value={form.guest_count} onChange={set("guest_count")} />
        </div>
        <Button type="submit" loading={saving}>
          Create plan
        </Button>
      </form>
    </section>
  );
}
