import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { Badge } from "../../components/StatusBadge";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate } from "../../lib/format";
import type { CustomerContact, Page, VendorSummary } from "../../types";

interface AdminReview {
  id: number;
  booking_id: number;
  rating: number;
  comment: string | null;
  is_visible: boolean;
  created_at: string;
  vendor: VendorSummary;
  customer: CustomerContact;
}

export default function AdminReviewsPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<AdminReview> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData((await api.get<Page<AdminReview>>("/admin/reviews", { params: { page, size: 20 } })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(r: AdminReview) {
    try {
      await api.patch(`/admin/reviews/${r.id}`, { is_visible: !r.is_visible });
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Reviews</h1>
        <p className="text-stone-600">Reviews come only from customers with completed bookings. Hidden reviews are kept but not shown or counted.</p>
      </div>
      {error && <Alert kind="error">{error}</Alert>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No reviews yet.</p>
      ) : (
        <ul className="space-y-3">
          {data.items.map((r) => (
            <li key={r.id} className="rounded-xl border border-maroon-100 bg-white p-4 text-sm shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p>
                    <span className="text-gold-500">{"★".repeat(r.rating)}</span>
                    <span className="text-stone-300">{"★".repeat(5 - r.rating)}</span>{" "}
                    for{" "}
                    <Link to={`/admin/vendors/${r.vendor.id}`} className="text-maroon-700 underline">
                      {r.vendor.business_name}
                    </Link>{" "}
                    {!r.is_visible && <Badge tone="grey">Hidden</Badge>}
                  </p>
                  <p className="text-stone-600">
                    by {r.customer.full_name} ({r.customer.email}) · booking #{r.booking_id} · {formatDate(r.created_at)}
                  </p>
                  {r.comment && <p className="mt-1 whitespace-pre-line">{r.comment}</p>}
                </div>
                <Button variant={r.is_visible ? "danger" : "secondary"} className="px-3 py-1.5" onClick={() => toggle(r)}>
                  {r.is_visible ? "Hide" : "Show"}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} noun="reviews" onPage={setPage} />}
    </section>
  );
}
