import { useEffect, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import SelectField from "../../components/SelectField";
import TextArea from "../../components/TextArea";
import { api, getErrorMessage } from "../../lib/api";
import type { Category, VendorInput, VendorPublic } from "../../types";

type Errors = Partial<Record<"business_name" | "category_id" | "contact_phone" | "contact_email" | "location" | "starting_price", string>>;

interface Props {
  initial?: VendorPublic;
  submitLabel: string;
  /** Called with the validated body; throw to show the error in the form. */
  onSubmit: (input: VendorInput) => Promise<void>;
  successMessage?: string;
}

export default function VendorProfileForm({ initial, submitLabel, onSubmit, successMessage }: Props) {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [form, setForm] = useState({
    business_name: initial?.business_name ?? "",
    category_id: initial ? String(initial.category.id) : "",
    description: initial?.description ?? "",
    contact_phone: initial?.contact_phone ?? "",
    contact_email: initial?.contact_email ?? "",
    location: initial?.location ?? "",
    service_areas: initial?.service_areas.join(", ") ?? "",
    starting_price: initial?.starting_price != null ? String(initial.starting_price) : "",
  });
  const [errors, setErrors] = useState<Errors>({});
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Categories always come from the database; nothing is hardcoded.
    api
      .get<Category[]>("/categories")
      .then((res) => setCategories(res.data))
      .catch((err) => setMessage({ kind: "error", text: getErrorMessage(err) }));
  }, []);

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  function validate(): Errors {
    const found: Errors = {};
    if (form.business_name.trim().length < 2) found.business_name = "Enter the business name";
    if (!form.category_id) found.category_id = "Choose a category";
    if (!/^(\+?91)?[6-9]\d{9}$/.test(form.contact_phone.replace(/[\s\-()]/g, ""))) {
      found.contact_phone = "Enter a valid 10-digit Indian mobile number";
    }
    if (form.contact_email && !/^\S+@\S+\.\S+$/.test(form.contact_email.trim())) found.contact_email = "Enter a valid email";
    if (form.location.trim().length < 2) found.location = "Enter the town or city";
    if (form.starting_price && !(Number(form.starting_price) >= 0)) found.starting_price = "Enter a valid amount";
    return found;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) return;

    setSaving(true);
    try {
      await onSubmit({
        business_name: form.business_name.trim(),
        category_id: Number(form.category_id),
        description: form.description.trim() || null,
        contact_phone: form.contact_phone.trim(),
        contact_email: form.contact_email.trim() || null,
        location: form.location.trim(),
        service_areas: form.service_areas.split(",").map((s) => s.trim()).filter(Boolean),
        starting_price: form.starting_price ? Number(form.starting_price) : null,
      });
      if (successMessage) setMessage({ kind: "success", text: successMessage });
    } catch (err) {
      setMessage({ kind: "error", text: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  // Keep the vendor's current category selectable even if it was later deactivated.
  const categoryOptions = (categories ?? []).map((c) => ({ value: String(c.id), label: c.name }));
  if (initial && !categoryOptions.some((o) => o.value === String(initial.category.id))) {
    categoryOptions.push({ value: String(initial.category.id), label: `${initial.category.name} (inactive)` });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      {categories && categories.length === 0 && (
        <Alert kind="info">No service categories exist yet. An administrator must create categories first.</Alert>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Business name" required value={form.business_name} onChange={set("business_name")} error={errors.business_name} maxLength={150} />
        <SelectField
          label="Category"
          required
          value={form.category_id}
          onChange={set("category_id")}
          error={errors.category_id}
          placeholder={categories ? "Select a category" : "Loading…"}
          options={categoryOptions}
        />
        <FormField label="Contact phone" type="tel" required value={form.contact_phone} onChange={set("contact_phone")} error={errors.contact_phone} />
        <FormField label="Contact email" type="email" value={form.contact_email} onChange={set("contact_email")} error={errors.contact_email} />
        <FormField label="Location" required value={form.location} onChange={set("location")} error={errors.location} hint="Town or city, e.g. Kamareddy" maxLength={120} />
        <FormField
          label="Starting price (₹)"
          type="number"
          min={0}
          step="0.01"
          value={form.starting_price}
          onChange={set("starting_price")}
          error={errors.starting_price}
          hint="Leave empty to show “Contact for pricing”."
        />
      </div>
      <FormField
        label="Service areas"
        value={form.service_areas}
        onChange={set("service_areas")}
        hint="Comma-separated, e.g. Kamareddy, Nizamabad, Yellareddy"
      />
      <TextArea label="Description" value={form.description} onChange={set("description")} maxLength={5000} rows={5} hint="Services offered, experience, style." />
      <Button type="submit" loading={saving}>
        {submitLabel}
      </Button>
    </form>
  );
}
