import { useCallback, useEffect, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import SelectField from "../../components/SelectField";
import Spinner from "../../components/Spinner";
import { api, getErrorMessage } from "../../lib/api";
import { AVAILABILITY_LABEL, formatDate, todayISO } from "../../lib/format";
import type { AvailabilityEntry, AvailabilityStatus } from "../../types";

const STATUS_STYLE: Record<AvailabilityStatus, string> = {
  available: "bg-green-100 text-green-800",
  tentative: "bg-amber-100 text-amber-900",
  booked: "bg-maroon-100 text-maroon-800",
  unavailable: "bg-stone-200 text-stone-700",
};

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Manage declared availability for `/me/vendor` (vendor) or `/admin/vendors/{id}` (admin). */
export default function AvailabilityManager({ basePath }: { basePath: string }) {
  const [entries, setEntries] = useState<AvailabilityEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState({ date: todayISO(), status: "available" as AvailabilityStatus, notes: "" });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const start = todayISO();
      const res = await api.get<AvailabilityEntry[]>(`${basePath}/availability`, { params: { start, end: addDays(start, 365) } });
      setEntries(res.data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [basePath]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      await api.put(`${basePath}/availability/${form.date}`, { availability_status: form.status, notes: form.notes.trim() || null });
      setNotice(`Saved ${formatDate(form.date)} as ${AVAILABILITY_LABEL[form.status].toLowerCase()}.`);
      setForm((f) => ({ ...f, notes: "" }));
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function clear(day: string) {
    setError(null);
    setNotice(null);
    try {
      await api.delete(`${basePath}/availability/${day}`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <div className="space-y-4">
      <Alert kind="info">
        Dates you mark here are shown to customers as your own declaration. Dates you leave empty show
        “Contact vendor to confirm availability”. A date is only guaranteed once a booking is confirmed.
      </Alert>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 rounded-xl border border-stone-200 bg-stone-50 p-4">
        <FormField label="Date" type="date" required min={todayISO()} value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        <SelectField
          label="Status"
          value={form.status}
          onChange={(e) => setForm({ ...form, status: e.target.value as AvailabilityStatus })}
          options={Object.entries(AVAILABILITY_LABEL).map(([value, label]) => ({ value, label }))}
        />
        <FormField label="Note" value={form.notes} maxLength={255} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="min-w-56 flex-1" />
        <Button type="submit" loading={saving} disabled={!form.date}>
          Save date
        </Button>
      </form>

      {!entries ? (
        <Spinner />
      ) : entries.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-6 text-center text-stone-600">
          No dates marked for the next 12 months.
        </p>
      ) : (
        <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
          {entries.map((entry) => (
            <li key={entry.date} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
              <span className="w-32 font-medium">{formatDate(entry.date)}</span>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[entry.availability_status]}`}>
                {AVAILABILITY_LABEL[entry.availability_status]}
              </span>
              <span className="flex-1 text-stone-600">{entry.notes}</span>
              <Button variant="secondary" className="px-2 py-1" onClick={() => clear(entry.date)}>
                Clear
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
