import { useEffect, useState } from "react";

import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import { api, getErrorMessage } from "../lib/api";
import type { Category } from "../types";

export default function HomePage() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Category[]>("/categories")
      .then((res) => setCategories(res.data))
      .catch((err) => setError(getErrorMessage(err)));
  }, []);

  return (
    <section className="space-y-10">
      <div className="max-w-2xl">
        <h1 className="font-display text-4xl font-semibold text-maroon-800">All your wedding services in one place</h1>
        <p className="mt-3 text-lg text-stone-600">
          Find photographers, decorators, caterers, DJs and more in Kamareddy. Compare packages and request quotations from one platform.
        </p>
      </div>

      <div>
        <h2 className="mb-4 text-xl font-semibold">Browse services</h2>
        {error ? (
          <Alert kind="error">{error}</Alert>
        ) : !categories ? (
          <Spinner />
        ) : categories.length === 0 ? (
          <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">
            Service categories will appear here soon.
          </p>
        ) : (
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {categories.map((c) => (
              <li key={c.id} className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
                {c.icon && <div className="text-3xl" aria-hidden>{c.icon}</div>}
                <p className="mt-2 font-semibold text-maroon-800">{c.name}</p>
                <p className="text-sm text-stone-600">
                  {c.vendor_count === 0 ? "Vendors coming soon" : `${c.vendor_count} ${c.vendor_count === 1 ? "vendor" : "vendors"}`}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
