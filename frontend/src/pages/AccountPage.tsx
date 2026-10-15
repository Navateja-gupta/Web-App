import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import Alert from "../components/Alert";
import Button from "../components/Button";
import FormField from "../components/FormField";
import { api, getErrorMessage } from "../lib/api";
import type { User } from "../types";

const ROLE_LABEL = { customer: "Customer", vendor: "Vendor", admin: "Administrator" } as const;

function ProfileForm({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [fullName, setFullName] = useState(user.full_name);
  const [phone, setPhone] = useState(user.phone ?? "");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    setSaving(true);
    try {
      const res = await api.patch<User>("/auth/me", { full_name: fullName.trim(), phone: phone.trim() || null });
      onSaved(res.data);
      setMessage({ kind: "success", text: "Profile updated." });
    } catch (err) {
      setMessage({ kind: "error", text: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <FormField label="Full name" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
      <FormField label="Mobile number" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} hint="Optional" />
      <FormField label="Email" value={user.email} disabled hint="Email cannot be changed yet." />
      <Button type="submit" loading={saving}>
        Save profile
      </Button>
    </form>
  );
}

function EmailPreference({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle(enabled: boolean) {
    setSaving(true);
    setError(null);
    try {
      onSaved((await api.patch<User>("/auth/me", { email_notifications: enabled })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-2">
      {error && <Alert kind="error">{error}</Alert>}
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          className="mt-1"
          checked={user.email_notifications}
          disabled={saving}
          onChange={(e) => toggle(e.target.checked)}
        />
        <span>
          <span className="block font-medium">Email me about important updates</span>
          <span className="block text-sm text-stone-600">
            New enquiries, quotations and booking changes are sent to {user.email}. Notifications in the app (the bell icon) are always on.
          </span>
        </span>
      </label>
    </div>
  );
}

function PasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    if (next !== confirm) {
      setMessage({ kind: "error", text: "New passwords do not match." });
      return;
    }
    setSaving(true);
    try {
      await api.post("/auth/change-password", { current_password: current, new_password: next });
      setCurrent("");
      setNext("");
      setConfirm("");
      setMessage({ kind: "success", text: "Password changed. You have been signed out on other devices." });
    } catch (err) {
      setMessage({ kind: "error", text: getErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <FormField label="Current password" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
      <FormField
        label="New password"
        type="password"
        autoComplete="new-password"
        required
        value={next}
        onChange={(e) => setNext(e.target.value)}
        hint="At least 8 characters with a letter and a number."
      />
      <FormField label="Confirm new password" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      <Button type="submit" loading={saving} disabled={!current || !next || !confirm}>
        Change password
      </Button>
    </form>
  );
}

export default function AccountPage() {
  const { user, setUser } = useAuth();
  if (!user) return null;

  return (
    <section className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">My account</h1>
        <p className="mt-1 text-stone-600">
          Signed in as <span className="font-medium">{user.email}</span> · {ROLE_LABEL[user.role]}
        </p>
      </div>

      {user.role === "vendor" && (
        <Alert kind="info">
          Manage your business profile, enquiries and bookings under{" "}
          <Link to="/vendor" className="underline">
            My business
          </Link>
          .
        </Alert>
      )}

      <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Profile</h2>
        <ProfileForm user={user} onSaved={setUser} />
      </div>

      <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Notifications</h2>
        <EmailPreference user={user} onSaved={setUser} />
      </div>

      <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Change password</h2>
        <PasswordForm />
      </div>
    </section>
  );
}
