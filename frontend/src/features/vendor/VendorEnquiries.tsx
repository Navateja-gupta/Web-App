import { useCallback, useEffect, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import Pagination from "../../components/Pagination";
import ReasonPrompt from "../../components/ReasonPrompt";
import Spinner from "../../components/Spinner";
import { EnquiryPill, QuotationPill } from "../../components/StatusPill";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import { ENQUIRY_LABEL, formatDate, formatINR, todayISO } from "../../lib/format";
import type { Enquiry, EnquiryStatus, Page } from "../../types";

const lines = (text: string) => text.split("\n").map((s) => s.trim()).filter(Boolean);

function QuoteForm({ enquiry, onSent, onCancel }: { enquiry: Enquiry; onSent: () => void; onCancel: () => void }) {
  const [form, setForm] = useState({ amount: "", description: "", inclusions: "", exclusions: "", validity: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (field: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [field]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!(Number(form.amount) >= 0) || form.amount === "") return setError("Enter the quoted amount.");
    setSaving(true);
    setError(null);
    try {
      await api.post(`/me/vendor/enquiries/${enquiry.id}/quotations`, {
        quoted_amount: Number(form.amount),
        description: form.description.trim() || null,
        inclusions: lines(form.inclusions),
        exclusions: lines(form.exclusions),
        validity_date: form.validity || null,
      });
      onSent();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-3 space-y-3 rounded-lg border border-stone-200 bg-stone-50 p-4" noValidate>
      {error && <Alert kind="error">{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Quoted amount (₹)" type="number" min={0} step="0.01" required value={form.amount} onChange={set("amount")} />
        <FormField label="Valid until" type="date" min={todayISO()} value={form.validity} onChange={set("validity")} hint="Optional" />
      </div>
      <TextArea label="Details" rows={3} maxLength={3000} value={form.description} onChange={set("description")} />
      <div className="grid gap-3 sm:grid-cols-2">
        <TextArea label="Included" rows={3} value={form.inclusions} onChange={set("inclusions")} hint="One per line" />
        <TextArea label="Not included" rows={3} value={form.exclusions} onChange={set("exclusions")} hint="One per line" />
      </div>
      {enquiry.quotations.some((q) => q.status === "sent") && (
        <p className="text-xs text-stone-500">Sending a new quotation replaces your earlier one.</p>
      )}
      <div className="flex gap-2">
        <Button type="submit" loading={saving}>
          Send quotation
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Back
        </Button>
      </div>
    </form>
  );
}

export default function VendorEnquiries() {
  const [status, setStatus] = useState<"" | EnquiryStatus>("pending");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Enquiry> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<{ id: number; kind: "quote" | "decline" } | null>(null);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<Enquiry>>("/me/vendor/enquiries", { params: { status: status || undefined, page, size: 10 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [status, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function withdraw(quotationId: number) {
    if (!window.confirm("Withdraw this quotation? The customer will no longer be able to accept it.")) return;
    try {
      await api.post(`/me/vendor/quotations/${quotationId}/withdraw`);
      setNotice("Quotation withdrawn.");
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <div className="space-y-4">
      <label className="text-sm text-stone-700">
        Show{" "}
        <select
          className="ml-1 rounded-lg border border-stone-300 bg-white px-2 py-1.5"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as "" | EnquiryStatus);
            setPage(1);
          }}
        >
          <option value="">All enquiries</option>
          {Object.entries(ENQUIRY_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {value === "pending" ? "New (awaiting your quotation)" : label}
            </option>
          ))}
        </select>
      </label>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No enquiries here.</p>
      ) : (
        <ul className="space-y-4">
          {data.items.map((e) => (
            <li key={e.id} className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    {formatDate(e.service_date)} · {e.event_location}
                  </p>
                  <p className="text-sm text-stone-600">
                    {e.guest_count ? `${e.guest_count} guests · ` : ""}
                    {e.budget !== null ? `Customer budget ${formatINR(e.budget)} · ` : ""}
                    received {formatDate(e.created_at)}
                  </p>
                </div>
                <EnquiryPill status={e.status} />
              </div>
              {e.customer && (
                <p className="mt-2 text-sm">
                  <span className="font-medium">{e.customer.full_name}</span>
                  {" · "}
                  <a href={`mailto:${e.customer.email}`} className="text-maroon-700 underline">
                    {e.customer.email}
                  </a>
                  {e.customer.phone && (
                    <>
                      {" · "}
                      <a href={`tel:${e.customer.phone}`} className="text-maroon-700 underline">
                        {e.customer.phone}
                      </a>
                    </>
                  )}
                </p>
              )}
              <p className="mt-2 whitespace-pre-line rounded-lg bg-stone-50 p-3 text-sm text-stone-700">{e.requirements}</p>

              {e.quotations.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm">
                  {e.quotations.map((q) => (
                    <li key={q.id} className="flex flex-wrap items-center justify-between gap-2">
                      <span>
                        Your quotation: <strong>{formatINR(q.quoted_amount)}</strong> on {formatDate(q.created_at)}
                      </span>
                      <span className="flex items-center gap-2">
                        <QuotationPill status={q.status} />
                        {q.status === "sent" && (
                          <Button variant="secondary" className="px-2 py-1" onClick={() => withdraw(q.id)}>
                            Withdraw
                          </Button>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              {(e.status === "pending" || e.status === "quoted") && !mode && (
                <div className="mt-3 flex gap-2">
                  <Button onClick={() => setMode({ id: e.id, kind: "quote" })}>{e.status === "quoted" ? "Revise quotation" : "Send quotation"}</Button>
                  <Button variant="secondary" onClick={() => setMode({ id: e.id, kind: "decline" })}>
                    Decline
                  </Button>
                </div>
              )}
              {mode?.id === e.id && mode.kind === "quote" && (
                <QuoteForm
                  enquiry={e}
                  onCancel={() => setMode(null)}
                  onSent={() => {
                    setMode(null);
                    setNotice("Quotation sent to the customer.");
                    void load();
                  }}
                />
              )}
              {mode?.id === e.id && mode.kind === "decline" && (
                <div className="mt-3">
                  <ReasonPrompt
                    label="Message to the customer (optional)"
                    confirmLabel="Decline enquiry"
                    required={false}
                    onCancel={() => setMode(null)}
                    onConfirm={async (reason) => {
                      try {
                        await api.post(`/me/vendor/enquiries/${e.id}/decline`, { reason: reason || null });
                        setMode(null);
                        setNotice("Enquiry declined.");
                        await load();
                      } catch (err) {
                        setError(getErrorMessage(err));
                      }
                    }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="enquiries" onPage={setPage} />}
    </div>
  );
}
