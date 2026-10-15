import type {
  ApprovalStatus,
  AvailabilityStatus,
  BookingStatus,
  EnquiryStatus,
  PlanItemStatus,
  PricingType,
  QuotationStatus,
  ReportReason,
  VendorPackage,
} from "../types";

export const ENQUIRY_LABEL: Record<EnquiryStatus, string> = {
  pending: "Waiting for vendor",
  quoted: "Quotation received",
  declined: "Declined by vendor",
  cancelled: "Cancelled",
  closed: "Closed",
};

export const QUOTATION_LABEL: Record<QuotationStatus, string> = {
  sent: "Awaiting your decision",
  accepted: "Accepted",
  rejected: "Declined",
  withdrawn: "Withdrawn",
  expired: "Expired",
};

export const BOOKING_LABEL: Record<BookingStatus, string> = {
  requested: "Awaiting vendor confirmation",
  confirmed: "Confirmed",
  completed: "Completed",
  cancelled: "Cancelled",
  rejected: "Not accepted by vendor",
};

export const PLAN_ITEM_LABEL: Record<PlanItemStatus, string> = {
  planned: "Planned",
  shortlisted: "Shortlisted",
  booked: "Booked",
  paid: "Paid",
  cancelled: "Cancelled",
};

export const REPORT_REASON_LABEL: Record<ReportReason, string> = {
  fake_listing: "Fake or misleading listing",
  wrong_information: "Wrong contact or business information",
  inappropriate_content: "Inappropriate photos or text",
  poor_service: "Poor service or unprofessional behaviour",
  other: "Something else",
};

/** Ratings are only shown when real reviews exist. */
export function ratingLabel(average: number | null, count: number): string | null {
  if (average === null || count === 0) return null;
  return `★ ${average.toFixed(1)} (${count} ${count === 1 ? "review" : "reviews"})`;
}

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

export function formatINR(amount: number): string {
  return inr.format(amount).replace(/\.00$/, "");
}

/** Never invent a price: vendors without one show "Contact for pricing". */
export function startingPriceLabel(price: number | null): string {
  return price === null ? "Contact for pricing" : `From ${formatINR(price)}`;
}

export const PRICING_TYPE_LABEL: Record<PricingType, string> = {
  fixed: "Fixed price",
  per_person: "Per person / per plate",
  starting_from: "Starting from",
  quote_on_request: "Quote on request",
};

export function packagePriceLabel(pkg: Pick<VendorPackage, "pricing_type" | "price" | "price_max">): string {
  if (pkg.pricing_type === "quote_on_request" || pkg.price === null) return "Contact for pricing";
  const range = pkg.price_max !== null ? `${formatINR(pkg.price)} – ${formatINR(pkg.price_max)}` : formatINR(pkg.price);
  if (pkg.pricing_type === "per_person") return `${range} per person`;
  if (pkg.pricing_type === "starting_from") return `From ${range}`;
  return range;
}

export const APPROVAL_LABEL: Record<ApprovalStatus, string> = {
  pending: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
  suspended: "Suspended",
};

export const AVAILABILITY_LABEL: Record<AvailabilityStatus, string> = {
  available: "Available",
  tentative: "Tentative",
  booked: "Booked",
  unavailable: "Unavailable",
};

export function formatDate(iso: string): string {
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Today's date as YYYY-MM-DD in the browser's local time zone. */
export function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
