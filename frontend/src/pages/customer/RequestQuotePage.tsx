import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import SelectField from "../../components/SelectField";
import Spinner from "../../components/Spinner";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import { todayISO } from "../../lib/format";
import type { VendorPublic, WeddingPlanSummary } from "../../types";

interface ShortlistItem {
  vendor: VendorPublic;
}

/** Send the same requirements to one or more vendors (from the profile page or the shortlist). */
export default function RequestQuotePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [vendors, setVendors] = useState<VendorPublic[] | null>(null);
  const [plans, setPlans] = useState<WeddingPlanSummary[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [form, setForm] = useState({ service_date: "", event_location: "", guest_count: "", budget: "", requirements: "", wedding_plan_id: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const slug = params.get("vendor");
    Promise.all([
      api.get<ShortlistItem[]>("/me/shortlist"),
      slug ? api.get<VendorPublic>(`/vendors/${encodeURIComponent(slug)}`) : Promise.resolve(null),
      api.get<WeddingPlanSummary[]>("/me/wedding-plans"),
    ])
      .then(([shortlist, single, planRes]) => {
        const list = shortlist.data.map((i) => i.vendor);
        if (single && !list.some((v) => v.id === single.data.id)) list.unshift(single.data);
        setVendors(list);
        setPlans(planRes.data);
        if (single) setSelected(new Set([single.data.id]));
        const plan = planRes.data[0];
        if (plan) {
          setForm((f) => ({
            ...f,
            wedding_plan_id: String(plan.id),
            service_date: plan.event_date && plan.event_date >= todayISO() ? plan.event_date : "",
            event_location: plan.location ?? "",
            guest_count: plan.guest_count ? String(plan.guest_count) : "",
          }));
        }
      })
      .catch((err) => setError(getErrorMessage(err)));
  }, [params]);

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [field]: e.target.value }));

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 10) next.add(id);
      return next;
    });
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (selected.size === 0) return setError("Choose at least one vendor.");
    if (!form.service_date) return setError("Choose the event date.");
    if (form.requirements.trim().length < 10) return setError("Describe your requirements in at least 10 characters.");
    setSaving(true);
    try {
      await api.post("/me/quotation-requests", {
        vendor_ids: [...selected],
        service_date: form.service_date,
        event_location: form.event_location.trim(),
        guest_count: form.guest_count ? Number(form.guest_count) : null,
        budget: form.budget ? Number(form.budget) : null,
        requirements: form.requirements.trim(),
        wedding_plan_id: form.wedding_plan_id ? Number(form.wedding_plan_id) : null,
      });
      navigate("/enquiries", { state: { sent: selected.size } });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (!vendors) return error ? <Alert kind="error">{error}</Alert> : <Spinner />;

  return (
    <section className="max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Request quotations</h1>
        <p className="text-stone-600">Describe your event once and send it to up to 10 vendors. Each vendor replies separately.</p>
      </div>

      <form onSubmit={submit} className="space-y-6" noValidate>
        {error && <Alert kind="error">{error}</Alert>}

        <fieldset className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
          <legend className="px-1 font-semibold">Vendors ({selected.size} selected)</legend>
          {vendors.length === 0 ? (
            <p className="text-sm text-stone-600">
              Your shortlist is empty.{" "}
              <Link to="/categories" className="text-maroon-700 underline">
                Browse vendors
              </Link>{" "}
              and save the ones you like.
            </p>
          ) : (
            <ul className="grid gap-2 sm:grid-cols-2">
              {vendors.map((v) => (
                <li key={v.id}>
                  <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-stone-200 p-3 hover:bg-maroon-50/40">
                    <input type="checkbox" className="mt-1" checked={selected.has(v.id)} onChange={() => toggle(v.id)} />
                    <span>
                      <span className="block font-medium">{v.business_name}</span>
                      <span className="text-sm text-stone-600">
                        {v.category.name} · {v.location}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        <fieldset className="grid gap-4 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm sm:grid-cols-2">
          <legend className="px-1 font-semibold">Event details</legend>
          {plans.length > 0 && (
            <SelectField
              label="Wedding plan"
              className="sm:col-span-2"
              value={form.wedding_plan_id}
              onChange={set("wedding_plan_id")}
              placeholder="Not linked to a plan"
              options={plans.map((p) => ({ value: String(p.id), label: p.event_name }))}
            />
          )}
          <FormField label="Event date" type="date" required min={todayISO()} value={form.service_date} onChange={set("service_date")} />
          <FormField label="Venue / location" required maxLength={255} value={form.event_location} onChange={set("event_location")} />
          <FormField label="Number of guests" type="number" min={1} value={form.guest_count} onChange={set("guest_count")} />
          <FormField label="Your budget (₹)" type="number" min={0} value={form.budget} onChange={set("budget")} hint="Optional" />
          <TextArea
            label="What do you need?"
            required
            className="sm:col-span-2"
            rows={5}
            maxLength={5000}
            value={form.requirements}
            onChange={set("requirements")}
            hint="Timings, style, special requests, vegetarian/non-vegetarian, etc."
          />
        </fieldset>

        <Button type="submit" loading={saving} disabled={selected.size === 0}>
          Send to {selected.size || ""} {selected.size === 1 ? "vendor" : "vendors"}
        </Button>
      </form>
    </section>
  );
}
