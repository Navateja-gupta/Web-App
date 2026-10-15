export type Role = "customer" | "vendor" | "admin";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  email_notifications: boolean;
  created_at: string;
}

export interface AppNotification {
  id: number;
  kind: string;
  title: string;
  body: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface CategorySummary {
  id: number;
  name: string;
  slug: string;
}

export interface Category extends CategorySummary {
  description: string | null;
  icon: string | null;
  display_order: number;
  is_active: boolean;
  vendor_count: number;
  created_at: string;
}

export type ApprovalStatus = "pending" | "approved" | "rejected" | "suspended";

export interface VendorPublic {
  id: number;
  slug: string;
  business_name: string;
  category: CategorySummary;
  description: string | null;
  contact_phone: string;
  contact_email: string | null;
  location: string;
  service_areas: string[];
  starting_price: number | null;
  is_verified: boolean;
  cover_image_url: string | null;
  rating_average: number | null;
  review_count: number;
}

export interface VendorOwner extends VendorPublic {
  approval_status: ApprovalStatus;
  is_active: boolean;
  status_reason: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VendorAdmin extends VendorOwner {
  user: { id: number; full_name: string; email: string } | null;
  verified_at: string | null;
  verification_notes: string | null;
  created_by_id: number | null;
  has_pending_claim_code: boolean;
}

/** Body for creating/updating a vendor profile. */
export interface VendorInput {
  business_name: string;
  category_id: number;
  description: string | null;
  contact_phone: string;
  contact_email: string | null;
  location: string;
  service_areas: string[];
  starting_price: number | null;
}

export type PricingType = "fixed" | "per_person" | "starting_from" | "quote_on_request";

export interface VendorPackage {
  id: number;
  vendor_id: number;
  name: string;
  description: string | null;
  pricing_type: PricingType;
  price: number | null;
  price_max: number | null;
  inclusions: string[];
  exclusions: string[];
  is_active: boolean;
}

export interface PortfolioItem {
  id: number;
  url: string;
  media_type: "image";
  caption: string | null;
  display_order: number;
  created_at: string;
}

// ---------- Planning, enquiries, bookings (Phase 5) ----------

export interface VendorSummary {
  id: number;
  slug: string;
  business_name: string;
  category: CategorySummary;
  contact_phone: string;
  location: string;
}

export interface CustomerContact {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
}

export type EnquiryStatus = "pending" | "quoted" | "declined" | "cancelled" | "closed";
export type QuotationStatus = "sent" | "accepted" | "rejected" | "withdrawn" | "expired";
export type BookingStatus = "requested" | "confirmed" | "completed" | "cancelled" | "rejected";
export type PlanItemStatus = "planned" | "shortlisted" | "booked" | "paid" | "cancelled";

export interface Quotation {
  id: number;
  quotation_request_id: number;
  vendor: VendorSummary;
  quoted_amount: number;
  description: string | null;
  inclusions: string[];
  exclusions: string[];
  validity_date: string | null;
  status: QuotationStatus;
  created_at: string;
}

export interface Enquiry {
  id: number;
  vendor: VendorSummary;
  service_date: string;
  event_location: string;
  guest_count: number | null;
  requirements: string;
  budget: number | null;
  status: EnquiryStatus;
  vendor_response: string | null;
  wedding_plan_id: number | null;
  created_at: string;
  updated_at: string;
  quotations: Quotation[];
  /** Present for vendor and admin views only. */
  customer?: CustomerContact;
}

export interface Booking {
  id: number;
  vendor: VendorSummary;
  customer: CustomerContact;
  package: { id: number; name: string } | null;
  quotation_id: number | null;
  wedding_plan_id: number | null;
  event_date: string;
  event_location: string | null;
  agreed_amount: number | null;
  booking_status: BookingStatus;
  notes: string | null;
  confirmed_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  has_review: boolean;
  created_at: string;
}

export interface BudgetSummary {
  estimated_budget: number | null;
  total_estimated: number;
  total_actual: number;
  committed: number;
  remaining: number | null;
  over_budget: boolean;
  item_count: number;
  by_status: Record<PlanItemStatus, number>;
}

export interface PlanItem {
  id: number;
  description: string;
  category: CategorySummary | null;
  vendor: { id: number; slug: string; business_name: string } | null;
  package_id: number | null;
  estimated_cost: number;
  actual_cost: number | null;
  status: PlanItemStatus;
  created_at: string;
}

export interface WeddingPlanSummary {
  id: number;
  event_name: string;
  event_date: string | null;
  location: string | null;
  estimated_budget: number | null;
  guest_count: number | null;
  created_at: string;
  updated_at: string;
  budget: BudgetSummary;
}

export interface WeddingPlan extends WeddingPlanSummary {
  items: PlanItem[];
}

export interface ReviewPublic {
  id: number;
  rating: number;
  comment: string | null;
  reviewer_name: string;
  created_at: string;
}

export interface VendorReviews {
  average: number | null;
  count: number;
  items: ReviewPublic[];
  page: number;
  pages: number;
}

export type ReportReason = "fake_listing" | "wrong_information" | "inappropriate_content" | "poor_service" | "other";

export type AvailabilityStatus = "available" | "tentative" | "booked" | "unavailable";

export interface AvailabilityEntry {
  date: string;
  availability_status: AvailabilityStatus;
  notes: string | null;
}
