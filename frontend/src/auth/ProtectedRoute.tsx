import type { ReactNode } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import Spinner from "../components/Spinner";
import type { Role } from "../types";
import { useAuth } from "./AuthContext";

/**
 * Hides pages from users who are not signed in or lack the role.
 * This is only for user experience; the backend enforces every permission.
 */
export default function ProtectedRoute({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner label="Checking your session…" />;

  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <section className="text-center">
        <h1 className="font-display text-2xl text-maroon-800">Access denied</h1>
        <p className="mt-2 text-stone-600">Your account does not have permission to view this page.</p>
        <Link to="/" className="mt-4 inline-block text-maroon-700 underline">
          Go to home page
        </Link>
      </section>
    );
  }

  return <>{children}</>;
}
