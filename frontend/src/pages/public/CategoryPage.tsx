import { AxiosError } from "axios";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Spinner from "../../components/Spinner";
import VendorBrowser from "../../features/marketplace/VendorBrowser";
import { api, getErrorMessage } from "../../lib/api";
import type { Category } from "../../types";

export default function CategoryPage() {
  const { slug = "" } = useParams();
  const [category, setCategory] = useState<Category | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setState("loading");
    api
      .get<Category>(`/categories/${encodeURIComponent(slug)}`)
      .then((r) => {
        setCategory(r.data);
        setState("ready");
      })
      .catch((err) => {
        if (err instanceof AxiosError && err.response?.status === 404) setState("missing");
        else {
          setError(getErrorMessage(err));
          setState("error");
        }
      });
  }, [slug]);

  if (state === "loading") return <Spinner />;
  if (state === "error") return <Alert kind="error">{error}</Alert>;
  if (state === "missing" || !category) {
    return (
      <section className="text-center">
        <h1 className="font-display text-2xl text-maroon-800">Service not found</h1>
        <p className="mt-2 text-stone-600">This service is not available.</p>
        <Link to="/categories" className="mt-4 inline-block text-maroon-700 underline">
          See all services
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <nav aria-label="Breadcrumb" className="text-sm text-stone-500">
        <Link to="/" className="hover:text-maroon-700">
          Home
        </Link>{" "}
        /{" "}
        <Link to="/categories" className="hover:text-maroon-700">
          Services
        </Link>{" "}
        / <span className="text-stone-700">{category.name}</span>
      </nav>
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">
          {category.icon && <span className="mr-2" aria-hidden>{category.icon}</span>}
          {category.name}
        </h1>
        {category.description && <p className="mt-1 text-stone-600">{category.description}</p>}
      </div>
      <VendorBrowser key={category.slug} fixedCategory={category.slug} />
    </section>
  );
}
