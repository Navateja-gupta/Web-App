import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export default function StatCard({ label, value, hint, to }: { label: string; value: ReactNode; hint?: string; to?: string }) {
  const body = (
    <>
      <p className="text-sm text-stone-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-maroon-800">{value}</p>
      {hint && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
    </>
  );
  const className = "block rounded-xl border border-maroon-100 bg-white p-4 shadow-sm";
  return to ? (
    <Link to={to} className={`${className} transition hover:border-maroon-300`}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  );
}
