import { Link } from "react-router-dom";

import { startingPriceLabel } from "../lib/format";
import type { VendorPublic } from "../types";
import ShortlistButton from "./ShortlistButton";
import { Badge } from "./StatusBadge";
import VendorImage from "./VendorImage";

export default function VendorCard({ vendor }: { vendor: VendorPublic }) {
  return (
    <article className="group flex flex-col overflow-hidden rounded-xl border border-maroon-100 bg-white shadow-sm transition hover:shadow-md">
      <Link to={`/vendors/${vendor.slug}`} className="block" tabIndex={-1} aria-hidden>
        <VendorImage src={vendor.cover_image_url} alt="" className="aspect-[4/3] w-full" />
      </Link>
      <div className="flex flex-1 flex-col gap-1 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold leading-snug">
            <Link to={`/vendors/${vendor.slug}`} className="text-stone-900 hover:text-maroon-700">
              {vendor.business_name}
            </Link>
          </h3>
          <ShortlistButton vendorId={vendor.id} compact />
        </div>
        <p className="text-sm text-stone-600">
          {vendor.category.name} · {vendor.location}
        </p>
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="text-sm font-medium text-maroon-800">{startingPriceLabel(vendor.starting_price)}</span>
          {vendor.is_verified && <Badge tone="blue">Verified</Badge>}
        </div>
      </div>
    </article>
  );
}
