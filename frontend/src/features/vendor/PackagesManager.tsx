import { useCallback, useEffect, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import SelectField from "../../components/SelectField";
import Spinner from "../../components/Spinner";
import { Badge } from "../../components/StatusBadge";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import { PRICING_TYPE_LABEL, packagePriceLabel } from "../../lib/format";
import type { PricingType, VendorPackage } from "../../types";

const lines = (text: string) => text.split("\n").map((s) => s.trim()).filter(Boolean);

function PackageForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: VendorPackage;
  onSave: (body: Record<string, unknown>) => Promise<void>;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState({
    name: initial?.name ?? "",
    pricing_type: (initial?.pricing_type ?? "fixed") as PricingType,
    price: initial?.price != null ? String(initial.price) : "",
    price_max: initial?.price_max != null ? String(initial.price_max) : "",
    description: initial?.description ?? "",
    inclusions: initial?.inclusions.join("\n") ?? "",
    exclusions: initial?.exclusions.join("\n") ?? "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const quote = form.pricing_type === "quote_on_request";
  const set = (field: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [field]: e.target.value }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.name.trim().length < 2) return setError("Enter a package name");
    if (!quote && form.price === "") return setError("Enter a price, or choose “Quote on request”");
    setSaving(true);
    try {
      await onSave({
        name: form.name.trim(),
        pricing_type: form.pricing_type,
        price: quote || form.price === "" ? null : Number(form.price),
        price_max: quote || form.price_max === "" ? null : Number(form.price_max),
        description: form.description.trim() || null,
        inclusions: lines(form.inclusions),
        exclusions: lines(form.exclusions),
      });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-stone-200 bg-stone-50 p-4" noValidate>
      {error && <Alert kind="error">{error}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Package name" required value={form.name} onChange={set("name")} maxLength={120} />
        <SelectField
          label="Pricing"
          value={form.pricing_type}
          onChange={set("pricing_type")}
          options={Object.entries(PRICING_TYPE_LABEL).map(([value, label]) => ({ value, label }))}
        />
        {!quote && (
          <>
            <FormField label="Price (₹)" type="number" min={0} step="0.01" required value={form.price} onChange={set("price")} />
            <FormField label="Maximum price (₹)" type="number" min={0} step="0.01" value={form.price_max} onChange={set("price_max")} hint="Optional, for a price range." />
          </>
        )}
      </div>
      <TextArea label="Description" value={form.description} onChange={set("description")} rows={3} maxLength={3000} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextArea label="Included" value={form.inclusions} onChange={set("inclusions")} rows={4} hint="One item per line." />
        <TextArea label="Not included" value={form.exclusions} onChange={set("exclusions")} rows={4} hint="One item per line." />
      </div>
      <div className="flex gap-2">
        <Button type="submit" loading={saving}>
          {initial ? "Save package" : "Add package"}
        </Button>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

/** Manage packages for `/me/vendor` (vendor) or `/admin/vendors/{id}` (admin). */
export default function PackagesManager({ basePath }: { basePath: string }) {
  const [packages, setPackages] = useState<VendorPackage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<"idle" | "add" | number>("idle");

  const load = useCallback(async () => {
    try {
      setPackages((await api.get<VendorPackage[]>(`${basePath}/packages`)).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [basePath]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  if (!packages) return error ? <Alert kind="error">{error}</Alert> : <Spinner />;

  return (
    <div className="space-y-4">
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      {mode === "add" ? (
        <PackageForm
          onCancel={() => setMode("idle")}
          onSave={async (body) => {
            await api.post(`${basePath}/packages`, body);
            setMode("idle");
            setNotice("Package added.");
            await load();
          }}
        />
      ) : (
        <Button onClick={() => setMode("add")}>Add package</Button>
      )}

      {packages.length === 0 && mode !== "add" && (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-6 text-center text-stone-600">
          No packages yet. Add packages so customers can compare what you offer.
        </p>
      )}

      <ul className="space-y-3">
        {packages.map((pkg) =>
          mode === pkg.id ? (
            <li key={pkg.id}>
              <PackageForm
                initial={pkg}
                onCancel={() => setMode("idle")}
                onSave={async (body) => {
                  await api.patch(`${basePath}/packages/${pkg.id}`, body);
                  setMode("idle");
                  setNotice("Package updated.");
                  await load();
                }}
              />
            </li>
          ) : (
            <li key={pkg.id} className="rounded-xl border border-stone-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">
                    {pkg.name} {!pkg.is_active && <Badge tone="grey">Hidden</Badge>}
                  </h3>
                  <p className="text-sm text-maroon-800">{packagePriceLabel(pkg)}</p>
                  {pkg.description && <p className="mt-1 whitespace-pre-line text-sm text-stone-600">{pkg.description}</p>}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => setMode(pkg.id)}>
                    Edit
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      run(
                        () => api.patch(`${basePath}/packages/${pkg.id}`, { is_active: !pkg.is_active }),
                        pkg.is_active ? "Package hidden from customers." : "Package is visible again.",
                      )
                    }
                  >
                    {pkg.is_active ? "Hide" : "Show"}
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() =>
                      window.confirm(`Delete package “${pkg.name}”?`) &&
                      run(() => api.delete(`${basePath}/packages/${pkg.id}`), "Package deleted.")
                    }
                  >
                    Delete
                  </Button>
                </div>
              </div>
              {(pkg.inclusions.length > 0 || pkg.exclusions.length > 0) && (
                <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  {pkg.inclusions.length > 0 && (
                    <div>
                      <p className="font-medium text-stone-700">Included</p>
                      <ul className="list-inside list-disc text-stone-600">
                        {pkg.inclusions.map((i) => <li key={i}>{i}</li>)}
                      </ul>
                    </div>
                  )}
                  {pkg.exclusions.length > 0 && (
                    <div>
                      <p className="font-medium text-stone-700">Not included</p>
                      <ul className="list-inside list-disc text-stone-600">
                        {pkg.exclusions.map((i) => <li key={i}>{i}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </li>
          ),
        )}
      </ul>
    </div>
  );
}
