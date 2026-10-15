import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import VendorCard from "../../components/VendorCard";
import { api, getErrorMessage } from "../../lib/api";
import { todayISO } from "../../lib/format";
import type { Category, Page, VendorPublic } from "../../types";

const PAGE_SIZE = 12;
const FILTER_KEYS = ["q", "category", "location", "min_price", "max_price", "date"] as const;
type FilterKey = (typeof FILTER_KEYS)[number];

const SORTS = [
  { value: "newest", label: "Newest" },
  { value: "price_low", label: "Price: low to high" },
  { value: "price_high", label: "Price: high to low" },
  { value: "name", label: "Name (A–Z)" },
  { value: "rating", label: "Top rated" },
];

const inputClass = "mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm";

/**
 * Server-side search: every filter, sort and page is sent to the API and kept in the URL
 * so results can be shared and the back button works.
 */
export default function VendorBrowser({ fixedCategory }: { fixedCategory?: string }) {
  const [params, setParams] = useSearchParams();
  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [data, setData] = useState<Page<VendorPublic> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const read = (key: FilterKey) => params.get(key) ?? "";
  const [draft, setDraft] = useState<Record<FilterKey, string>>(() =>
    Object.fromEntries(FILTER_KEYS.map((k) => [k, read(k)])) as Record<FilterKey, string>,
  );
  const sort = params.get("sort") ?? "newest";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const category = fixedCategory ?? read("category");

  // Keep the form in sync when the URL changes (back/forward, links).
  useEffect(() => {
    setDraft(Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ""])) as Record<FilterKey, string>);
  }, [params]);

  useEffect(() => {
    if (!fixedCategory) api.get<Category[]>("/categories").then((r) => setCategories(r.data)).catch(() => undefined);
    api.get<string[]>("/vendors/locations").then((r) => setLocations(r.data)).catch(() => undefined);
  }, [fixedCategory]);

  const queryKey = params.toString();
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<Page<VendorPublic>>("/vendors", {
        params: {
          q: read("q") || undefined,
          category: category || undefined,
          location: read("location") || undefined,
          min_price: read("min_price") || undefined,
          max_price: read("max_price") || undefined,
          available_on: read("date") || undefined,
          sort,
          page,
          size: PAGE_SIZE,
        },
      })
      .then((res) => !cancelled && setData(res.data))
      .catch((err) => !cancelled && setError(getErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey, category]);

  function apply(changes: Record<string, string>, resetPage = true) {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (resetPage) next.delete("page");
    setParams(next);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    apply(Object.fromEntries(FILTER_KEYS.map((k) => [k, draft[k].trim()])));
  }

  function clearAll() {
    const next = new URLSearchParams();
    if (params.get("sort")) next.set("sort", params.get("sort")!);
    setParams(next);
  }

  const activeFilters = FILTER_KEYS.filter((k) => (fixedCategory && k === "category" ? false : !!read(k))).length;
  const set = (key: FilterKey) => (e: { target: { value: string } }) => setDraft((d) => ({ ...d, [key]: e.target.value }));

  return (
    <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
      <form onSubmit={submit} className="h-fit space-y-4 rounded-xl border border-maroon-100 bg-white p-4 shadow-sm" aria-label="Filter vendors">
        <label className="block text-sm font-medium text-stone-700">
          Search
          <input className={inputClass} value={draft.q} onChange={set("q")} placeholder="Name or service" maxLength={100} />
        </label>
        {!fixedCategory && (
          <label className="block text-sm font-medium text-stone-700">
            Category
            <select className={inputClass} value={draft.category} onChange={set("category")}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="block text-sm font-medium text-stone-700">
          Location
          <select className={inputClass} value={draft.location} onChange={set("location")}>
            <option value="">Any location</option>
            {draft.location && !locations.includes(draft.location) && <option value={draft.location}>{draft.location}</option>}
            {locations.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <fieldset>
          <legend className="text-sm font-medium text-stone-700">Starting price (₹)</legend>
          <div className="mt-1 grid grid-cols-2 gap-2">
            <input className={inputClass.replace("mt-1 ", "")} type="number" min={0} placeholder="Min" aria-label="Minimum price" value={draft.min_price} onChange={set("min_price")} />
            <input className={inputClass.replace("mt-1 ", "")} type="number" min={0} placeholder="Max" aria-label="Maximum price" value={draft.max_price} onChange={set("max_price")} />
          </div>
          <p className="mt-1 text-xs text-stone-500">Vendors without published prices are hidden when a price filter is used.</p>
        </fieldset>
        <label className="block text-sm font-medium text-stone-700">
          Available on
          <input className={inputClass} type="date" min={todayISO()} value={draft.date} onChange={set("date")} />
          <span className="mt-1 block text-xs font-normal text-stone-500">Shows vendors who have marked this date as available.</span>
        </label>
        <div className="flex gap-2">
          <Button type="submit" className="flex-1">
            Apply
          </Button>
          {activeFilters > 0 && (
            <Button type="button" variant="secondary" onClick={clearAll}>
              Clear
            </Button>
          )}
        </div>
      </form>

      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-stone-600" aria-live="polite">
            {data ? `${data.total} ${data.total === 1 ? "vendor" : "vendors"} found` : " "}
          </p>
          <label className="text-sm text-stone-700">
            Sort by{" "}
            <select className="ml-1 rounded-lg border border-stone-300 bg-white px-2 py-1.5" value={sort} onChange={(e) => apply({ sort: e.target.value })}>
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && <Alert kind="error">{error}</Alert>}

        {loading && !data ? (
          <Spinner label="Finding vendors…" />
        ) : data && data.items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-stone-300 bg-white p-10 text-center">
            <p className="font-medium">No vendors match your search.</p>
            <p className="mt-1 text-sm text-stone-600">
              {activeFilters > 0 ? "Try removing some filters." : "New vendors are being added. Please check back soon."}
            </p>
            {activeFilters > 0 && (
              <Button variant="secondary" className="mt-4" onClick={clearAll}>
                Clear filters
              </Button>
            )}
          </div>
        ) : (
          data && (
            <>
              <ul className={`grid gap-4 sm:grid-cols-2 xl:grid-cols-3 ${loading ? "opacity-60" : ""}`}>
                {data.items.map((v) => (
                  <li key={v.id}>
                    <VendorCard vendor={v} />
                  </li>
                ))}
              </ul>
              <Pagination
                page={data.page}
                pages={data.pages}
                total={data.total}
                noun="vendors"
                onPage={(p) => {
                  apply({ page: String(p) }, false);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              />
            </>
          )
        )}
      </div>
    </div>
  );
}
