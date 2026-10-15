import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { homePathFor, useAuth } from "../auth/AuthContext";
import Alert from "../components/Alert";
import Button from "../components/Button";
import FormField from "../components/FormField";
import { getErrorMessage } from "../lib/api";

/** Only allow same-site relative redirects (prevents open-redirect via ?next=). */
function safeNext(next: string | null): string | null {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={next ?? homePathFor(user.role)} replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const loggedIn = await login(email.trim(), password);
      navigate(next ?? homePathFor(loggedIn.role), { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-md">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">Log in</h1>
      <p className="mt-2 text-stone-600">Customers, vendors and administrators all log in here.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-xl border border-maroon-100 bg-white p-6 shadow-sm" noValidate>
        {error && <Alert kind="error">{error}</Alert>}
        <FormField label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <FormField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" loading={submitting} disabled={!email || !password} className="w-full">
          Log in
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-stone-600">
        New here?{" "}
        <Link to="/register" className="text-maroon-700 underline">
          Create a customer account
        </Link>{" "}
        or{" "}
        <Link to="/vendor/register" className="text-maroon-700 underline">
          register your business
        </Link>
        .
      </p>
    </section>
  );
}
