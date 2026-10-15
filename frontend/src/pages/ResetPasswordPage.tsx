import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import Alert from "../components/Alert";
import Button from "../components/Button";
import FormField from "../components/FormField";
import Spinner from "../components/Spinner";
import { api, getErrorMessage } from "../lib/api";

/** Read the token from the URL fragment (#token=...), which is never sent to any server. */
function readToken(): string {
  return new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token") ?? "";
}

export default function ResetPasswordPage() {
  const { user, logout } = useAuth();
  const [token] = useState(readToken);
  const [state, setState] = useState<"checking" | "ready" | "invalid" | "done">("checking");
  const [firstName, setFirstName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Remove the token from the address bar and browser history.
    window.history.replaceState(null, "", window.location.pathname);
    if (!token) {
      setState("invalid");
      return;
    }
    api
      .post<{ first_name: string }>("/auth/password-reset/verify", { token })
      .then((r) => {
        setFirstName(r.data.first_name);
        setState("ready");
      })
      .catch((err) => {
        setError(getErrorMessage(err));
        setState("invalid");
      });
  }, [token]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      return setError("Use at least 8 characters with a letter and a number.");
    }
    if (password !== confirm) return setError("Passwords do not match.");
    setSaving(true);
    try {
      await api.post("/auth/password-reset", { token, new_password: password });
      // All sessions were revoked on the server; clear any local signed-in state too.
      if (user) await logout();
      setState("done");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mx-auto max-w-md space-y-6">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">Set a new password</h1>

      {state === "checking" && <Spinner label="Checking your link…" />}

      {state === "invalid" && (
        <div className="space-y-4">
          <Alert kind="error">{error ?? "This reset link is missing or incomplete. Open the full link you were sent."}</Alert>
          <p className="text-sm text-stone-600">
            Links work once and expire after 24 hours. Please{" "}
            <Link to="/contact" className="text-maroon-700 underline">
              contact us
            </Link>{" "}
            for a new one.
          </p>
        </div>
      )}

      {state === "ready" && (
        <form onSubmit={submit} className="space-y-4 rounded-xl border border-maroon-100 bg-white p-6 shadow-sm" noValidate>
          <p className="text-stone-700">Hello {firstName}, choose a new password for your account.</p>
          {error && <Alert kind="error">{error}</Alert>}
          <FormField
            label="New password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            hint="At least 8 characters with a letter and a number."
          />
          <FormField label="Confirm new password" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <Button type="submit" loading={saving} className="w-full">
            Save new password
          </Button>
        </form>
      )}

      {state === "done" && (
        <div className="space-y-4">
          <Alert kind="success">Your password has been changed. For your security, you have been signed out on all devices.</Alert>
          <Link to="/login" className="inline-block rounded-lg bg-maroon-700 px-5 py-2 text-white hover:bg-maroon-800">
            Log in with your new password
          </Link>
        </div>
      )}
    </section>
  );
}
