import { useEffect, useState } from "react";

import Alert from "../../components/Alert";
import Spinner from "../../components/Spinner";
import StatCard from "../../components/StatCard";
import { api, getErrorMessage } from "../../lib/api";
import { APPROVAL_LABEL, BOOKING_LABEL, ENQUIRY_LABEL, formatINR } from "../../lib/format";
import type { ApprovalStatus, BookingStatus, EnquiryStatus } from "../../types";

interface Stats {
  users_by_role: Record<"customer" | "vendor" | "admin", number>;
  new_users_last_30_days: number;
  vendors_by_status: Record<ApprovalStatus, number>;
  live_vendors_by_category: { category: string; vendors: number }[];
  categories_active: number;
  enquiries_by_status: Record<EnquiryStatus, number>;
  bookings_by_status: Record<BookingStatus, number>;
  confirmed_booking_value: number;
  reviews_visible: number;
  open_reports: number;
}

function Breakdown<K extends string>({ title, data, labels }: { title: string; data: Record<K, number>; labels: Record<K, string> }) {
  const total = Object.values<number>(data).reduce((a, b) => a + b, 0);
  return (
    <div className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
      <h2 className="mb-3 font-semibold">
        {title} <span className="font-normal text-stone-500">({total})</span>
      </h2>
      <ul className="space-y-2 text-sm">
        {(Object.keys(labels) as K[]).map((key) => (
          <li key={key}>
            <div className="flex justify-between">
              <span>{labels[key]}</span>
              <span className="font-medium">{data[key] ?? 0}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-stone-100">
              <div className="h-1.5 rounded-full bg-maroon-600" style={{ width: total ? `${((data[key] ?? 0) / total) * 100}%` : 0 }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Stats>("/admin/stats")
      .then((r) => setStats(r.data))
      .catch((err) => setError(getErrorMessage(err)));
  }, []);

  if (error) return <Alert kind="error">{error}</Alert>;
  if (!stats) return <Spinner />;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Marketplace overview</h1>
        <p className="text-stone-600">Live figures from the database.</p>
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Vendors awaiting approval" value={stats.vendors_by_status.pending} to="/admin/vendors" />
        <StatCard label="Live vendors" value={stats.vendors_by_status.approved} />
        <StatCard label="Customers" value={stats.users_by_role.customer} hint={`${stats.new_users_last_30_days} new users in 30 days`} to="/admin/users" />
        <StatCard label="Open complaints" value={stats.open_reports} to="/admin/reports" />
        <StatCard label="Active categories" value={stats.categories_active} to="/admin/categories" />
        <StatCard label="Confirmed booking value" value={formatINR(stats.confirmed_booking_value)} hint="Confirmed + completed bookings" />
        <StatCard label="Published reviews" value={stats.reviews_visible} to="/admin/reviews" />
        <StatCard label="Vendor accounts" value={stats.users_by_role.vendor} />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Breakdown title="Vendors" data={stats.vendors_by_status} labels={APPROVAL_LABEL} />
        <Breakdown title="Enquiries" data={stats.enquiries_by_status} labels={ENQUIRY_LABEL} />
        <Breakdown title="Bookings" data={stats.bookings_by_status} labels={BOOKING_LABEL} />
      </div>
      <div className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-semibold">Live vendors by category</h2>
        {stats.live_vendors_by_category.length === 0 ? (
          <p className="text-sm text-stone-600">No active categories.</p>
        ) : (
          <ul className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            {stats.live_vendors_by_category.map((row) => (
              <li key={row.category} className="flex justify-between rounded-lg bg-stone-50 px-3 py-2">
                <span>{row.category}</span>
                <span className="font-medium">{row.vendors}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
