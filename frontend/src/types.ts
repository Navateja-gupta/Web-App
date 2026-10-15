export type Role = "customer" | "vendor" | "admin";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
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

export type AvailabilityStatus = "available" | "tentative" | "booked" | "unavailable";

export interface AvailabilityEntry {
  date: string;
  availability_status: AvailabilityStatus;
  notes: string | null;
}
