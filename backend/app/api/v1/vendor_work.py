"""Vendor workspace: incoming enquiries, quotations and bookings for the vendor's own business."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.my_vendor import my_vendor_access
from app.api.v1.vendor_resources import VendorAccess
from app.db.session import get_db
from app.dependencies.pagination import PageParams, get_page_params
from app.models.enums import BookingStatus, QuotationRequestStatus
from app.schemas.booking import BookingConfirm, BookingRead, BookingReason
from app.schemas.common import Page
from app.schemas.quotation import DeclineRequest, EnquiryRead, QuotationCreate
from app.services import bookings as booking_service
from app.services import quotations as quotation_service

router = APIRouter(prefix="/me/vendor", tags=["vendor: enquiries & bookings"])


# ---------- Enquiries ----------

@router.get("/enquiries", response_model=Page[EnquiryRead])
def list_enquiries(
    status_filter: QuotationRequestStatus | None = Query(default=None, alias="status"),
    params: PageParams = Depends(get_page_params),
    access: VendorAccess = Depends(my_vendor_access),
    db: Session = Depends(get_db),
) -> Page[EnquiryRead]:
    items, total = quotation_service.list_vendor_enquiries(db, access.vendor, params, status_filter)
    return Page[EnquiryRead].build([EnquiryRead.model_validate(i) for i in items], total, params.page, params.size)


@router.get("/enquiries/{request_id}", response_model=EnquiryRead)
def get_enquiry(request_id: int, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return quotation_service.get_vendor_enquiry(db, access.vendor, request_id)


@router.post("/enquiries/{request_id}/quotations", response_model=EnquiryRead, status_code=status.HTTP_201_CREATED)
def send_quotation(
    request_id: int, data: QuotationCreate, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    """Send a quotation. Sending again replaces your previous quotation for this enquiry."""
    return quotation_service.send_quotation(db, access.vendor, access.actor, request_id, data)


@router.post("/enquiries/{request_id}/decline", response_model=EnquiryRead)
def decline_enquiry(
    request_id: int, data: DeclineRequest, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    return quotation_service.decline_enquiry(db, access.vendor, access.actor, request_id, data.reason)


@router.post("/quotations/{quotation_id}/withdraw", response_model=EnquiryRead)
def withdraw_quotation(quotation_id: int, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return quotation_service.withdraw_quotation(db, access.vendor, access.actor, quotation_id)


# ---------- Bookings ----------

@router.get("/bookings", response_model=Page[BookingRead])
def list_bookings(
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    params: PageParams = Depends(get_page_params),
    access: VendorAccess = Depends(my_vendor_access),
    db: Session = Depends(get_db),
) -> Page[BookingRead]:
    items, total = booking_service.list_bookings(db, params, vendor=access.vendor, status=status_filter)
    return Page[BookingRead].build([BookingRead.model_validate(b) for b in items], total, params.page, params.size)


@router.get("/bookings/{booking_id}", response_model=BookingRead)
def get_booking(booking_id: int, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return booking_service.get_booking(db, booking_id, vendor=access.vendor)


@router.post("/bookings/{booking_id}/confirm", response_model=BookingRead)
def confirm_booking(
    booking_id: int, data: BookingConfirm, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    booking = booking_service.get_booking(db, booking_id, vendor=access.vendor)
    return booking_service.change_status(db, booking, "confirm", access.actor, agreed_amount=data.agreed_amount)


def _reason_action(action: str):  # type: ignore[no-untyped-def]
    def handler(
        booking_id: int,
        data: BookingReason,
        access: VendorAccess = Depends(my_vendor_access),
        db: Session = Depends(get_db),
    ) -> BookingRead:
        booking = booking_service.get_booking(db, booking_id, vendor=access.vendor)
        return BookingRead.model_validate(booking_service.change_status(db, booking, action, access.actor, reason=data.reason))

    handler.__name__ = f"{action}_booking"
    return handler


router.post("/bookings/{booking_id}/reject", response_model=BookingRead)(_reason_action("reject"))
router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)(_reason_action("cancel"))


@router.post("/bookings/{booking_id}/complete", response_model=BookingRead)
def complete_booking(booking_id: int, access: VendorAccess = Depends(my_vendor_access), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    """Mark a confirmed booking as completed (on or after the event date). Customers can then review."""
    booking = booking_service.get_booking(db, booking_id, vendor=access.vendor)
    return booking_service.change_status(db, booking, "complete", access.actor)
