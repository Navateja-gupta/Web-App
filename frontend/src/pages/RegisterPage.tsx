import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { homePathFor, useAuth } from "../auth/AuthContext";
import Alert from "../components/Alert";
import Button from "../components/Button";
import FormField from "../components/FormField";
import { getErrorMessage } from "../lib/api";

type Errors = Partial<Record<"full_name" | "email" | "phone" | "password" | "confirm", string>>;

function validate(form: { full_name: string; email: string; phone: string; password: string; confirm: string }): Errors {
  const errors: Errors = {};
  if (form.full_name.trim().length < 2) errors.full_name = "Enter your full name";
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) errors.email = "Enter a valid email address";
  if (form.phone && !/^(\+?91)?[6-9]\d{9}$/.test(form.phone.replace(/[\s\-()]/g, ""))) {
    errors.phone = "Enter a valid 10-digit Indian mobile number";
  }
  if (form.password.length < 8) errors.password = "Use at least 8 characters";
  else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
    errors.password = "Include at least one letter and one number";
  }
  if (form.confirm !== form.password) errors.confirm = "Passwords do not match";
  return errors;
}

export default function RegisterPage({ role }: { role: "customer" | "vendor" }) {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "", confirm: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  const isVendor = role === "vendor";
  const update = (field: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setServerError(null);
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      const created = await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || undefined,
        password: form.password,
        role,
      });
      navigate(homePathFor(created.role), { replace: true });
    } catch (err) {
      setServerError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-md">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">
        {isVendor ? "Register your business" : "Create your account"}
      </h1>
      <p className="mt-2 text-stone-600">
        {isVendor
          ? "Create a vendor account first. You will then add your business profile, which appears publicly after an administrator approves it."
          : "Save vendors, request quotations and plan your wedding budget in one place."}
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-xl border border-maroon-100 bg-white p-6 shadow-sm" noValidate>
        {serverError && <Alert kind="error">{serverError}</Alert>}
        <FormField label="Full name" autoComplete="name" required value={form.full_name} onChange={update("full_name")} error={errors.full_name} />
        <FormField label="Email" type="email" autoComplete="email" required value={form.email} onChange={update("email")} error={errors.email} />
        <FormField
          label="Mobile number"
          type="tel"
          autoComplete="tel"
          value={form.phone}
          onChange={update("phone")}
          error={errors.phone}
          hint="Optional. 10-digit Indian mobile number."
        />
        <FormField
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          value={form.password}
          onChange={update("password")}
          error={errors.password}
          hint="At least 8 characters with a letter and a number."
        />
        <FormField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          value={form.confirm}
          onChange={update("confirm")}
          error={errors.confirm}
        />
        <Button type="submit" loading={submitting} className="w-full">
          {isVendor ? "Create vendor account" : "Create account"}
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-stone-600">
        Already registered?{" "}
        <Link to="/login" className="text-maroon-700 underline">
          Log in
        </Link>
        {" · "}
        {isVendor ? (
          <Link to="/register" className="text-maroon-700 underline">
            Sign up as a customer instead
          </Link>
        ) : (
          <Link to="/vendor/register" className="text-maroon-700 underline">
            Register as a vendor instead
          </Link>
        )}
      </p>
    </section>
  );
}
