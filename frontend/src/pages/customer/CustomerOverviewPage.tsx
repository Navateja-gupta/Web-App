import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import Alert from "../../components/Alert";
import Spinner from "../../components/Spinner";
import StatCard from "../../components/StatCard";
import { BookingPill } from "../../components/StatusPill";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate, formatINR } from "../../lib/format";
import type { Booking, Enquiry, Page, Quotation, WeddingPlanSummary } from "../../types";

interface Overview {
  plans: WeddingPlanSummary[];
  enquiries: Enquiry[];
  quotations: Quotation[];
  bookings: Booking[];
  shortlistCount: number;
}

export default function CustomerOverviewPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<WeddingPlanSummary[]>("/me/wedding-plans"),
      api.get<Enquiry[]>("/me/quotation-requests"),
      api.get<Quotation[]>("/me/quotations", { params: { status: "sent" } }),
      api.get<Page<Booking>>("/me/bookings", { params: { size: 100 } }),
      api.get<number[]>("/me/shortlist/ids"),
    ])
      .then(([plans, enquiries, quotations, bookings, shortlist]) =>
        setData({
          plans: plans.data,
          enquiries: enquiries.data,
          quotations: quotations.data,
          bookings: bookings.data.items,
          shortlistCount: shortlist.data.length,
        }),
      )
      .catch((err) => setError(getErrorMessage(err)));
  }, []);

  if (error) return <Alert kind="error">{error}</Alert>;
  if (!data) return <Spinner />;

  const openEnquiries = data.enquiries.filter((e) => e.status === "pending" || e.status === "quoted").length;
  const upcoming = data.bookings.filter((b) => b.booking_status === "requested" || b.booking_status === "confirmed");
  const toReview = data.bookings.filter((b) => b.booking_status === "completed" && !b.has_review);

  return (
    <section className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Hello, {user?.full_name.split(" ")[0]}</h1>
        <p className="text-stone-600">Everything for your wedding in one place.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Shortlisted vendors" value={data.shortlistCount} to="/shortlist" />
        <StatCard label="Open enquiries" value={openEnquiries} to="/enquiries" />
        <StatCard label="Quotations to review" value={data.quotations.length} to="/quotations" />
        <StatCard label="Upcoming bookings" value={upcoming.length} to="/bookings" />
      </div>

      {toReview.length > 0 && (
        <Alert kind="info">
          You have {toReview.length} completed {toReview.length === 1 ? "booking" : "bookings"} to review.{" "}
          <Link to="/bookings" className="underline">
            Leave a review
          </Link>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Your events</h2>
            <Link to="/plans" className="text-sm text-maroon-700 underline">
              Manage
            </Link>
          </div>
          {data.plans.length === 0 ? (
            <p className="text-sm text-stone-600">
              No events yet.{" "}
              <Link to="/plans" className="text-maroon-700 underline">
                Create your wedding plan
              </Link>{" "}
              to track your budget.
            </p>
          ) : (
            <ul className="divide-y divide-stone-100">
              {data.plans.map((p) => (
                <li key={p.id} className="flex items-center justify-between py-2 text-sm">
                  <Link to={`/plans/${p.id}`} className="font-medium text-maroon-700 hover:underline">
                    {p.event_name}
                  </Link>
                  <span className="text-stone-600">
                    {p.event_date ? formatDate(p.event_date) : "Date not set"}
                    {p.budget.remaining !== null && (
                      <span className={p.budget.over_budget ? " text-red-700" : ""}> · {formatINR(p.budget.remaining)} left</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Upcoming bookings</h2>
            <Link to="/bookings" className="text-sm text-maroon-700 underline">
              All bookings
            </Link>
          </div>
          {upcoming.length === 0 ? (
            <p className="text-sm text-stone-600">No upcoming bookings. Request quotations from your shortlisted vendors to get started.</p>
          ) : (
            <ul className="divide-y divide-stone-100">
              {upcoming.slice(0, 5).map((b) => (
                <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                  <span>
                    <span className="font-medium">{b.vendor.business_name}</span> · {formatDate(b.event_date)}
                  </span>
                  <BookingPill status={b.booking_status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
