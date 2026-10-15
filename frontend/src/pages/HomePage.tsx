import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import Alert from "../components/Alert";
import Spinner from "../components/Spinner";
import VendorCard from "../components/VendorCard";
import { api, getErrorMessage } from "../lib/api";
import type { Category, Page, VendorPublic } from "../types";

export default function HomePage() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [recent, setRecent] = useState<VendorPublic[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [location, setLocation] = useState("");

  useEffect(() => {
    api
      .get<Category[]>("/categories")
      .then((res) => setCategories(res.data))
      .catch((err) => setError(getErrorMessage(err)));
    api.get<Page<VendorPublic>>("/vendors", { params: { size: 6, sort: "newest" } }).then((r) => setRecent(r.data.items)).catch(() => undefined);
    api.get<string[]>("/vendors/locations").then((r) => setLocations(r.data)).catch(() => undefined);
  }, []);

  function search(e: FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (location) params.set("location", location);
    navigate(`/search?${params.toString()}`);
  }

  return (
    <div className="space-y-14">
      <section className="rounded-2xl bg-gradient-to-br from-maroon-800 to-maroon-600 px-6 py-12 text-white sm:px-10">
        <h1 className="max-w-2xl font-display text-4xl font-semibold leading-tight sm:text-5xl">All your wedding services in one place</h1>
        <p className="mt-4 max-w-2xl text-lg text-maroon-50">
          Find and compare photographers, decorators, caterers, DJs and more in Kamareddy, without calling around.
        </p>
        <form onSubmit={search} className="mt-8 flex max-w-3xl flex-col gap-2 rounded-xl bg-white p-2 sm:flex-row" role="search">
          <label className="sr-only" htmlFor="home-q">
            What are you looking for?
          </label>
          <input
            id="home-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Photographer, mehendi, veg catering…"
            maxLength={100}
            className="flex-1 rounded-lg px-3 py-2 text-stone-900 focus:outline-none focus:ring-2 focus:ring-maroon-600"
          />
          <label className="sr-only" htmlFor="home-location">
            Location
          </label>
          <select
            id="home-location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="rounded-lg border border-stone-200 px-3 py-2 text-stone-900"
          >
            <option value="">Any location</option>
            {locations.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <button type="submit" className="rounded-lg bg-gold-500 px-6 py-2 font-semibold text-maroon-900 hover:bg-gold-400">
            Search
          </button>
        </form>
      </section>

      <section>
        <div className="mb-4 flex items-end justify-between">
          <h2 className="font-display text-2xl font-semibold text-maroon-800">Browse by service</h2>
          <Link to="/categories" className="text-sm text-maroon-700 underline">
            All services
          </Link>
        </div>
        {error ? (
          <Alert kind="error">{error}</Alert>
        ) : !categories ? (
          <Spinner />
        ) : categories.length === 0 ? (
          <p className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center text-stone-600">Service categories will appear here soon.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {categories.map((c) => (
              <li key={c.id}>
                <Link
                  to={`/categories/${c.slug}`}
                  className="block h-full rounded-xl border border-maroon-100 bg-white p-5 shadow-sm transition hover:border-maroon-300 hover:shadow-md"
                >
                  {c.icon && <div className="text-3xl" aria-hidden>{c.icon}</div>}
                  <p className="mt-2 font-semibold text-maroon-800">{c.name}</p>
                  <p className="text-sm text-stone-600">
                    {c.vendor_count === 0 ? "Vendors coming soon" : `${c.vendor_count} ${c.vendor_count === 1 ? "vendor" : "vendors"}`}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {recent.length > 0 && (
        <section>
          <div className="mb-4 flex items-end justify-between">
            <h2 className="font-display text-2xl font-semibold text-maroon-800">Recently joined</h2>
            <Link to="/search" className="text-sm text-maroon-700 underline">
              See all vendors
            </Link>
          </div>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {recent.map((v) => (
              <li key={v.id}>
                <VendorCard vendor={v} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="grid gap-6 rounded-2xl border border-maroon-100 bg-white p-8 sm:grid-cols-3">
        {[
          ["Discover", "Browse local vendors by service, location and starting price."],
          ["Compare", "See packages, what is included, and real photos of past work."],
          ["Shortlist", "Save the vendors you like and come back to them any time."],
        ].map(([title, text]) => (
          <div key={title}>
            <h3 className="font-semibold text-maroon-800">{title}</h3>
            <p className="mt-1 text-sm text-stone-600">{text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
