import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "../../components/Alert";
import Spinner from "../../components/Spinner";
import { api, getErrorMessage } from "../../lib/api";
import type { Category } from "../../types";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Category[]>("/categories")
      .then((r) => setCategories(r.data))
      .catch((err) => setError(getErrorMessage(err)));
  }, []);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Wedding services</h1>
        <p className="text-stone-600">Choose a service to see the vendors available in and around Kamareddy.</p>
      </div>
      {error ? (
        <Alert kind="error">{error}</Alert>
      ) : !categories ? (
        <Spinner />
      ) : categories.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">No services are listed yet.</p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((c) => (
            <li key={c.id}>
              <Link
                to={`/categories/${c.slug}`}
                className="flex h-full gap-4 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm transition hover:border-maroon-300 hover:shadow-md"
              >
                {c.icon && <span className="text-4xl" aria-hidden>{c.icon}</span>}
                <span>
                  <span className="block text-lg font-semibold text-maroon-800">{c.name}</span>
                  {c.description && <span className="block text-sm text-stone-600">{c.description}</span>}
                  <span className="mt-1 block text-sm text-stone-500">
                    {c.vendor_count === 0 ? "Vendors coming soon" : `${c.vendor_count} ${c.vendor_count === 1 ? "vendor" : "vendors"}`}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
