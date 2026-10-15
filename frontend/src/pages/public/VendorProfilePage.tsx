import { AxiosError } from "axios";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Alert from "../../components/Alert";
import ShortlistButton from "../../components/ShortlistButton";
import Spinner from "../../components/Spinner";
import { Badge } from "../../components/StatusBadge";
import VendorImage from "../../components/VendorImage";
import { ReportListing, RequestQuoteButton, ReviewsSection, Stars } from "../../features/marketplace/VendorProfileExtras";
import { api, getErrorMessage } from "../../lib/api";
import { AVAILABILITY_LABEL, formatDate, packagePriceLabel, startingPriceLabel, todayISO } from "../../lib/format";
import type { AvailabilityEntry, PortfolioItem, VendorPackage, VendorPublic } from "../../types";

const UNCONFIRMED = "Contact vendor to confirm availability.";

function Gallery({ items, name }: { items: PortfolioItem[]; name: string }) {
  const [index, setIndex] = useState(0);
  if (items.length === 0) return <VendorImage src={null} alt="" className="aspect-[16/9] w-full rounded-xl" />;
  const current = items[Math.min(index, items.length - 1)];

  return (
    <div className="space-y-2">
      <figure className="overflow-hidden rounded-xl bg-stone-100">
        <img src={current.url} alt={current.caption ?? `${name} photo ${index + 1}`} className="aspect-[16/9] w-full object-contain" />
        {current.caption && <figcaption className="bg-white px-3 py-2 text-sm text-stone-600">{current.caption}</figcaption>}
      </figure>
      {items.length > 1 && (
        <ul className="flex gap-2 overflow-x-auto pb-1" aria-label="Photos">
          {items.map((item, i) => (
            <li key={item.id} className="shrink-0">
              <button
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`Show photo ${i + 1}`}
                aria-current={i === index}
                className={`block overflow-hidden rounded-lg border-2 ${i === index ? "border-maroon-600" : "border-transparent"}`}
              >
                <img src={item.url} alt="" loading="lazy" className="h-16 w-24 object-cover" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AvailabilityBox({ entries }: { entries: AvailabilityEntry[] }) {
  const [date, setDate] = useState("");
  const byDate = useMemo(() => new Map(entries.map((e) => [e.date, e])), [entries]);
  const checked = date ? byDate.get(date) : undefined;
  const upcoming = entries.filter((e) => e.availability_status === "available").slice(0, 6);

  return (
    <div className="space-y-3">
      <h2 className="font-semibold">Availability</h2>
      <label className="block text-sm text-stone-700">
        Check a date
        <input
          type="date"
          min={todayISO()}
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="mt-1 block w-full rounded-lg border border-stone-300 px-3 py-2"
        />
      </label>
      {date && (
        <p className="rounded-lg bg-stone-50 px-3 py-2 text-sm" aria-live="polite">
          {checked ? (
            <>
              <strong>{formatDate(date)}:</strong> vendor has marked this date as {AVAILABILITY_LABEL[checked.availability_status].toLowerCase()}.
              {checked.availability_status !== "booked" && checked.availability_status !== "unavailable" && ` ${UNCONFIRMED}`}
            </>
          ) : (
            <>
              <strong>{formatDate(date)}:</strong> {UNCONFIRMED}
            </>
          )}
        </p>
      )}
      {upcoming.length > 0 ? (
        <div className="text-sm text-stone-600">
          <p>Dates the vendor has marked available:</p>
          <p className="mt-1">{upcoming.map((e) => formatDate(e.date)).join(", ")}</p>
        </div>
      ) : (
        !date && <p className="text-sm text-stone-600">{UNCONFIRMED}</p>
      )}
      <p className="text-xs text-stone-500">Availability is declared by the vendor and is only guaranteed once a booking is confirmed.</p>
    </div>
  );
}

export default function VendorProfilePage() {
  const { slug = "" } = useParams();
  const [vendor, setVendor] = useState<VendorPublic | null>(null);
  const [packages, setPackages] = useState<VendorPackage[]>([]);
  const [photos, setPhotos] = useState<PortfolioItem[]>([]);
  const [availability, setAvailability] = useState<AvailabilityEntry[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    const base = `/vendors/${encodeURIComponent(slug)}`;
    const start = todayISO();
    const end = new Date();
    end.setDate(end.getDate() + 365);
    Promise.all([
      api.get<VendorPublic>(base),
      api.get<VendorPackage[]>(`${base}/packages`),
      api.get<PortfolioItem[]>(`${base}/portfolio`),
      api.get<AvailabilityEntry[]>(`${base}/availability`, { params: { start, end: end.toISOString().slice(0, 10) } }),
    ])
      .then(([v, p, ph, a]) => {
        if (cancelled) return;
        setVendor(v.data);
        setPackages(p.data);
        setPhotos(ph.data);
        setAvailability(a.data);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof AxiosError && err.response?.status === 404) setState("missing");
        else {
          setError(getErrorMessage(err));
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (vendor) document.title = `${vendor.business_name} · Kamareddy Wedding Services`;
    return () => {
      document.title = "Kamareddy Wedding Services";
    };
  }, [vendor]);

  if (state === "loading") return <Spinner />;
  if (state === "error") return <Alert kind="error">{error}</Alert>;
  if (state === "missing" || !vendor) {
    return (
      <section className="text-center">
        <h1 className="font-display text-2xl text-maroon-800">Vendor not found</h1>
        <p className="mt-2 text-stone-600">This vendor is not listed right now.</p>
        <Link to="/search" className="mt-4 inline-block text-maroon-700 underline">
          Browse vendors
        </Link>
      </section>
    );
  }

  return (
    <article className="space-y-6">
      <nav aria-label="Breadcrumb" className="text-sm text-stone-500">
        <Link to="/" className="hover:text-maroon-700">
          Home
        </Link>{" "}
        /{" "}
        <Link to={`/categories/${vendor.category.slug}`} className="hover:text-maroon-700">
          {vendor.category.name}
        </Link>{" "}
        / <span className="text-stone-700">{vendor.business_name}</span>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800 sm:text-4xl">{vendor.business_name}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-stone-600">
            <span>{vendor.category.name}</span>·<span>{vendor.location}</span>
            {vendor.is_verified && <Badge tone="blue">Verified by our team</Badge>}
          </p>
          {vendor.rating_average !== null && vendor.review_count > 0 && (
            <p className="mt-1 text-sm text-stone-700">
              <Stars value={vendor.rating_average} /> {vendor.rating_average.toFixed(1)} · {vendor.review_count}{" "}
              {vendor.review_count === 1 ? "review" : "reviews"}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ShortlistButton vendorId={vendor.id} />
          <RequestQuoteButton slug={vendor.slug} />
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-8">
          <Gallery items={photos} name={vendor.business_name} />

          {vendor.description && (
            <section>
              <h2 className="mb-2 text-xl font-semibold">About</h2>
              <p className="whitespace-pre-line text-stone-700">{vendor.description}</p>
            </section>
          )}

          <section>
            <h2 className="mb-3 text-xl font-semibold">Packages</h2>
            {packages.length === 0 ? (
              <p className="rounded-xl border border-dashed border-stone-300 bg-white p-6 text-stone-600">
                This vendor has not published packages yet. Contact them for pricing.
              </p>
            ) : (
              <ul className="grid gap-4 md:grid-cols-2">
                {packages.map((pkg) => (
                  <li key={pkg.id} className="flex flex-col rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
                    <h3 className="font-semibold">{pkg.name}</h3>
                    <p className="text-lg font-semibold text-maroon-800">{packagePriceLabel(pkg)}</p>
                    {pkg.description && <p className="mt-2 whitespace-pre-line text-sm text-stone-600">{pkg.description}</p>}
                    {pkg.inclusions.length > 0 && (
                      <div className="mt-3 text-sm">
                        <p className="font-medium text-stone-700">Included</p>
                        <ul className="mt-1 space-y-0.5 text-stone-600">
                          {pkg.inclusions.map((i) => (
                            <li key={i}>✓ {i}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {pkg.exclusions.length > 0 && (
                      <div className="mt-3 text-sm">
                        <p className="font-medium text-stone-700">Not included</p>
                        <ul className="mt-1 space-y-0.5 text-stone-600">
                          {pkg.exclusions.map((i) => (
                            <li key={i}>✕ {i}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <ReviewsSection slug={vendor.slug} />
        </div>

        <aside className="space-y-5">
          <div className="space-y-3 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
            <p className="text-sm text-stone-500">Starting price</p>
            <p className="text-2xl font-semibold text-maroon-800">{vendor.starting_price === null ? "Contact for pricing" : startingPriceLabel(vendor.starting_price)}</p>
            <div className="space-y-1 border-t border-stone-100 pt-3 text-sm">
              <p className="font-medium text-stone-700">Contact</p>
              <a href={`tel:${vendor.contact_phone}`} className="block text-maroon-700 underline">
                {vendor.contact_phone}
              </a>
              {vendor.contact_email && (
                <a href={`mailto:${vendor.contact_email}`} className="block break-all text-maroon-700 underline">
                  {vendor.contact_email}
                </a>
              )}
            </div>
            {vendor.service_areas.length > 0 && (
              <div className="border-t border-stone-100 pt-3 text-sm">
                <p className="font-medium text-stone-700">Serves</p>
                <ul className="mt-1 flex flex-wrap gap-1.5">
                  {vendor.service_areas.map((a) => (
                    <li key={a} className="rounded-full bg-maroon-50 px-2.5 py-0.5 text-maroon-800">
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
            <AvailabilityBox entries={availability} />
          </div>
          <ReportListing vendorId={vendor.id} />
        </aside>
      </div>
    </article>
  );
}
