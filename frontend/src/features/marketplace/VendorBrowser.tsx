import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
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
const TYPING_DELAY_MS = 450;
const FILTER_KEYS = ["q", "category", "location", "min_price", "max_price", "date"] as const;
type FilterKey = (typeof FILTER_KEYS)[number];
type Filters = Record<FilterKey, string>;
// Fields the user types into; these are applied after a short pause instead of on every keystroke.
const TYPED_KEYS: FilterKey[] = ["q", "min_price", "max_price"];

const SORTS = [
  { value: "newest", label: "Newest" },
  { value: "price_low", label: "Price: low to high" },
  { value: "price_high", label: "Price: high to low" },
  { value: "name", label: "Name (A–Z)" },
  { value: "rating", label: "Top rated" },
];

const inputClass = "mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm";

function filtersFrom(params: URLSearchParams): Filters {
  return Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ""])) as Filters;
}

function priceRangeError(f: Filters): string | null {
  const min = f.min_price.trim();
  const max = f.max_price.trim();
  if ((min && !(Number(min) >= 0)) || (max && !(Number(max) >= 0))) return "Enter prices as positive numbers.";
  if (min && max && Number(min) > Number(max)) return "Minimum price is more than the maximum.";
  return null;
}

/**
 * Server-side search that updates as filters change. Every filter, sort and page is kept
 * in the URL so results can be shared and the back button works.
 */
export default function VendorBrowser({ fixedCategory }: { fixedCategory?: string }) {
  const [params, setParams] = useSearchParams();
  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [data, setData] = useState<Page<VendorPublic> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // What the form shows. Typed fields may run ahead of the URL until the user pauses.
  const [form, setForm] = useState<Filters>(() => filtersFrom(params));
  const typingTimer = useRef<number | undefined>(undefined);

  const read = (key: FilterKey) => params.get(key) ?? "";
  const sort = params.get("sort") ?? "newest";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const category = fixedCategory ?? read("category");
  const rangeError = priceRangeError(form);

  // Keep the form in sync when the URL changes from outside (back/forward, links, Clear).
  useEffect(() => {
    setForm(filtersFrom(params));
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

  /** Write filters to the URL, which triggers the search. Always resets to page 1. */
  const commit = useCallback(
    (filters: Filters, { replace }: { replace: boolean }) => {
      if (priceRangeError(filters)) return; // keep showing the last valid results
      window.clearTimeout(typingTimer.current);
      const next = new URLSearchParams(params);
      FILTER_KEYS.forEach((k) => {
        const value = filters[k].trim();
        if (value) next.set(k, value);
        else next.delete(k);
      });
      next.delete("page");
      if (next.toString() !== params.toString()) setParams(next, { replace });
    },
    [params, setParams],
  );

  useEffect(() => () => window.clearTimeout(typingTimer.current), []);

  /** Dropdowns and the date picker apply immediately. */
  function choose(key: FilterKey, value: string) {
    const next = { ...form, [key]: value };
    setForm(next);
    commit(next, { replace: false });
  }

  /** Typed fields apply after a short pause (replace: no Back-button entry per keystroke). */
  function type(key: FilterKey, value: string) {
    const next = { ...form, [key]: value };
    setForm(next);
    window.clearTimeout(typingTimer.current);
    typingTimer.current = window.setTimeout(() => commit(next, { replace: true }), TYPING_DELAY_MS);
  }

  function submit(e: FormEvent) {
    e.preventDefault(); // Enter applies typed fields right away
    commit(form, { replace: false });
  }

  function changeSort(value: string) {
    const next = new URLSearchParams(params);
    next.set("sort", value);
    next.delete("page");
    setParams(next);
  }

  function clearAll() {
    window.clearTimeout(typingTimer.current);
    const next = new URLSearchParams();
    if (params.get("sort")) next.set("sort", params.get("sort")!);
    setParams(next);
  }

  const activeFilters = FILTER_KEYS.filter((k) => (fixedCategory && k === "category" ? false : !!form[k].trim())).length;
  const typingPending = TYPED_KEYS.some((k) => form[k].trim() !== read(k)) && !rangeError;

  return (
    <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
      <form onSubmit={submit} className="h-fit space-y-4 rounded-xl border border-maroon-100 bg-white p-4 shadow-sm" aria-label="Filter vendors">
        <label className="block text-sm font-medium text-stone-700">
          Search
          <input
            type="search"
            className={inputClass}
            value={form.q}
            onChange={(e) => type("q", e.target.value)}
            placeholder="Name or service"
            maxLength={100}
          />
        </label>
        {!fixedCategory && (
          <label className="block text-sm font-medium text-stone-700">
            Category
            <select className={inputClass} value={form.category} onChange={(e) => choose("category", e.target.value)}>
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
          <select className={inputClass} value={form.location} onChange={(e) => choose("location", e.target.value)}>
            <option value="">Any location</option>
            {form.location && !locations.includes(form.location) && <option value={form.location}>{form.location}</option>}
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
            <input
              className={inputClass.replace("mt-1 ", "")}
              type="number"
              min={0}
              inputMode="numeric"
              placeholder="Min"
              aria-label="Minimum price"
              aria-invalid={rangeError ? true : undefined}
              value={form.min_price}
              onChange={(e) => type("min_price", e.target.value)}
            />
            <input
              className={inputClass.replace("mt-1 ", "")}
              type="number"
              min={0}
              inputMode="numeric"
              placeholder="Max"
              aria-label="Maximum price"
              aria-invalid={rangeError ? true : undefined}
              value={form.max_price}
              onChange={(e) => type("max_price", e.target.value)}
            />
          </div>
          {rangeError ? (
            <p className="mt-1 text-xs text-red-700">{rangeError}</p>
          ) : (
            <p className="mt-1 text-xs text-stone-500">Vendors without published prices are hidden when a price filter is used.</p>
          )}
        </fieldset>
        <label className="block text-sm font-medium text-stone-700">
          Available on
          <input className={inputClass} type="date" min={todayISO()} value={form.date} onChange={(e) => choose("date", e.target.value)} />
          <span className="mt-1 block text-xs font-normal text-stone-500">Shows vendors who have marked this date as available.</span>
        </label>
        {activeFilters > 0 && (
          <Button type="button" variant="secondary" className="w-full" onClick={clearAll}>
            Clear filters
          </Button>
        )}
        {/* Hidden submit so pressing Enter in a text field applies immediately. */}
        <button type="submit" className="hidden" aria-hidden tabIndex={-1} />
      </form>

      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-stone-600" aria-live="polite">
            {loading || typingPending ? "Searching…" : data ? `${data.total} ${data.total === 1 ? "vendor" : "vendors"} found` : " "}
          </p>
          <label className="text-sm text-stone-700">
            Sort by{" "}
            <select className="ml-1 rounded-lg border border-stone-300 bg-white px-2 py-1.5" value={sort} onChange={(e) => changeSort(e.target.value)}>
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
              <ul className={`grid gap-4 transition-opacity sm:grid-cols-2 xl:grid-cols-3 ${loading ? "opacity-60" : ""}`}>
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
                  const next = new URLSearchParams(params);
                  next.set("page", String(p));
                  setParams(next);
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
