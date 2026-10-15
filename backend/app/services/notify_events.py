"""Who gets told about what. Each function only queues notifications; the caller commits.

Vendors created by an administrator may have no linked login yet. For those, the
administrators are notified instead so that nobody's enquiry is silently missed.
"""

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.enums import ApprovalStatus, BookingStatus, UserRole
from app.models.quotation import Quotation, QuotationRequest
from app.models.user import User
from app.models.vendor import Vendor
from app.services.notifications import active_admins, notify


def _fmt_date(value) -> str:  # type: ignore[no-untyped-def]
    return value.strftime("%d %b %Y")


def _inr(amount) -> str:  # type: ignore[no-untyped-def]
    return f"₹{amount:,.0f}" if amount == int(amount) else f"₹{amount:,.2f}"


def _notify_vendor_side(
    db: Session, vendor: Vendor, *, kind: str, title: str, body: str, vendor_link: str, admin_link: str
) -> None:
    if vendor.user is not None and vendor.user.is_active:
        notify(db, [vendor.user], kind=kind, title=title, body=body, link=vendor_link)
    else:
        notify(
            db,
            active_admins(db),
            kind=kind,
            title=f"[No vendor login] {title}",
            body=f"{body}\n\n{vendor.business_name} has no linked vendor account, so they were not notified. "
            f"Please contact them on {vendor.contact_phone}, or give them a claim code.",
            link=admin_link,
        )


# ---------- Enquiries & quotations ----------

def enquiry_created(db: Session, request: QuotationRequest, vendor: Vendor, customer: User) -> None:
    guests = f", {request.guest_count} guests" if request.guest_count else ""
    _notify_vendor_side(
        db,
        vendor,
        kind="enquiry.created",
        title=f"New enquiry for {_fmt_date(request.service_date)}",
        body=f"{customer.full_name} sent an enquiry to {vendor.business_name} for "
        f"{_fmt_date(request.service_date)} at {request.event_location}{guests}.",
        vendor_link="/vendor?tab=enquiries",
        admin_link="/admin/enquiries",
    )


def quotation_received(db: Session, request: QuotationRequest, quotation: Quotation, vendor: Vendor) -> None:
    notify(
        db,
        [request.customer],
        kind="quotation.received",
        title=f"Quotation from {vendor.business_name}",
        body=f"{vendor.business_name} quoted {_inr(quotation.quoted_amount)} for your event on "
        f"{_fmt_date(request.service_date)}. Compare and decide in your account.",
        link="/quotations",
    )


def enquiry_declined(db: Session, request: QuotationRequest, vendor: Vendor) -> None:
    message = f" Their message: {request.vendor_response}" if request.vendor_response else ""
    notify(
        db,
        [request.customer],
        kind="enquiry.declined",
        title=f"{vendor.business_name} can't take your enquiry",
        body=f"{vendor.business_name} declined your enquiry for {_fmt_date(request.service_date)}.{message}",
        link="/enquiries",
        email=False,
    )


# ---------- Bookings ----------

def booking_requested(db: Session, booking: Booking, vendor: Vendor, customer: User) -> None:
    amount = f" for {_inr(booking.agreed_amount)}" if booking.agreed_amount is not None else ""
    _notify_vendor_side(
        db,
        vendor,
        kind="booking.requested",
        title=f"Booking request for {_fmt_date(booking.event_date)}",
        body=f"{customer.full_name} requested a booking with {vendor.business_name} on "
        f"{_fmt_date(booking.event_date)}{amount}. Please confirm or decline it.",
        vendor_link="/vendor?tab=bookings",
        admin_link="/admin/bookings",
    )


def booking_status_changed(db: Session, booking: Booking, actor: User) -> None:
    vendor = booking.vendor
    customer = booking.customer
    date = _fmt_date(booking.event_date)
    reason = f" Reason: {booking.cancellation_reason}" if booking.cancellation_reason else ""
    status = booking.booking_status

    if status == BookingStatus.CONFIRMED:
        notify(db, [customer], kind="booking.confirmed", title=f"{vendor.business_name} confirmed your booking",
               body=f"Your booking with {vendor.business_name} on {date} is confirmed"
               f"{f' for {_inr(booking.agreed_amount)}' if booking.agreed_amount is not None else ''}.",
               link="/bookings")
    elif status == BookingStatus.REJECTED:
        notify(db, [customer], kind="booking.rejected", title=f"{vendor.business_name} could not accept your booking",
               body=f"{vendor.business_name} could not accept your booking for {date}.{reason}", link="/bookings")
    elif status == BookingStatus.COMPLETED:
        notify(db, [customer], kind="booking.completed", title=f"How was {vendor.business_name}?",
               body=f"Your booking with {vendor.business_name} on {date} is complete. You can now leave a review.",
               link="/bookings", email=False)
    elif status == BookingStatus.CANCELLED:
        title = f"Booking on {date} was cancelled"
        body = f"The booking between {customer.full_name} and {vendor.business_name} on {date} was cancelled.{reason}"
        if actor.role != UserRole.CUSTOMER:
            notify(db, [customer], kind="booking.cancelled", title=title, body=body, link="/bookings")
        if actor.role != UserRole.VENDOR:
            _notify_vendor_side(db, vendor, kind="booking.cancelled", title=title, body=body,
                                vendor_link="/vendor?tab=bookings", admin_link="/admin/bookings")


# ---------- Vendor onboarding ----------

def vendor_needs_review(db: Session, vendor: Vendor, *, resubmitted: bool) -> None:
    what = "updated their profile and needs review again" if resubmitted else "registered and is waiting for approval"
    notify(
        db,
        active_admins(db),
        kind="vendor.pending",
        title=f"Vendor waiting for approval: {vendor.business_name}",
        body=f"{vendor.business_name} ({vendor.category.name}, {vendor.location}) {what}.",
        link=f"/admin/vendors/{vendor.id}",
    )


def vendor_decision(db: Session, vendor: Vendor) -> None:
    if vendor.user is None:
        return
    status = vendor.approval_status
    reason = f" Reason: {vendor.status_reason}" if vendor.status_reason else ""
    if status == ApprovalStatus.APPROVED:
        title, body = "Your business is live", f"{vendor.business_name} is approved and now visible to customers."
    elif status == ApprovalStatus.REJECTED:
        title = "Your business profile needs changes"
        body = f"{vendor.business_name} was not approved.{reason} Update your profile and save to send it for review again."
    elif status == ApprovalStatus.SUSPENDED:
        title, body = "Your listing is suspended", f"{vendor.business_name} has been suspended.{reason}"
    else:
        return
    notify(db, [vendor.user], kind=f"vendor.{status.value}", title=title, body=body, link="/vendor?tab=profile")


def report_created(db: Session, target: str) -> None:
    notify(db, active_admins(db), kind="report.created", title="New complaint received",
           body=f"A user reported {target}. Please review it.", link="/admin/reports", email=False)
