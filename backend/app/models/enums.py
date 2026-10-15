"""Status/role values used by the models.

These are workflow states defined by the code, so they live here rather than in
the database. Business data (categories, vendors, prices) is never hardcoded.
"""

import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ADMIN = "admin"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class PricingType(str, enum.Enum):
    FIXED = "fixed"
    PER_PERSON = "per_person"
    STARTING_FROM = "starting_from"
    QUOTE_ON_REQUEST = "quote_on_request"


class MediaType(str, enum.Enum):
    IMAGE = "image"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    TENTATIVE = "tentative"
    BOOKED = "booked"
    UNAVAILABLE = "unavailable"


class QuotationRequestStatus(str, enum.Enum):
    PENDING = "pending"
    QUOTED = "quoted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class QuotationStatus(str, enum.Enum):
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class PlanItemStatus(str, enum.Enum):
    PLANNED = "planned"
    SHORTLISTED = "shortlisted"
    BOOKED = "booked"
    PAID = "paid"
    CANCELLED = "cancelled"


class ReportReason(str, enum.Enum):
    FAKE_LISTING = "fake_listing"
    WRONG_INFORMATION = "wrong_information"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    POOR_SERVICE = "poor_service"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class BookingStatus(str, enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
