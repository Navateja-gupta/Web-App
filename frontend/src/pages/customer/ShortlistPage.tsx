import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "../../components/Alert";
import Spinner from "../../components/Spinner";
import VendorCard from "../../components/VendorCard";
import { api, getErrorMessage } from "../../lib/api";
import { useShortlist } from "../../shortlist/ShortlistContext";
import type { VendorPublic } from "../../types";

interface ShortlistItem {
  vendor: VendorPublic;
  added_at: string;
}

export default function ShortlistPage() {
  const { isShortlisted } = useShortlist();
  const [items, setItems] = useState<ShortlistItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<ShortlistItem[]>("/me/shortlist")
      .then((r) => setItems(r.data))
      .catch((err) => setError(getErrorMessage(err)));
  }, []);

  // Removing a vendor with the Saved button hides it immediately.
  const visible = items?.filter((i) => isShortlisted(i.vendor.id)) ?? null;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">My shortlist</h1>
          <p className="text-stone-600">Vendors you have saved for your wedding.</p>
        </div>
        {visible && visible.length > 0 && (
          <Link to="/request-quote" className="rounded-lg bg-maroon-700 px-4 py-2 text-sm font-medium text-white hover:bg-maroon-800">
            Request quotations
          </Link>
        )}
      </div>
      {error ? (
        <Alert kind="error">{error}</Alert>
      ) : !visible ? (
        <Spinner />
      ) : visible.length === 0 ? (
        <div className="rounded-xl border border-dashed border-stone-300 bg-white p-10 text-center">
          <p className="font-medium">Your shortlist is empty.</p>
          <p className="mt-1 text-sm text-stone-600">Tap “Save” on any vendor to keep them here.</p>
          <Link to="/categories" className="mt-4 inline-block rounded-lg bg-maroon-700 px-4 py-2 text-sm font-medium text-white hover:bg-maroon-800">
            Browse services
          </Link>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((item) => (
            <li key={item.vendor.id}>
              <VendorCard vendor={item.vendor} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
