from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ReportReason, ReportStatus
from app.schemas.common import clean_optional_text
from app.schemas.parties import CustomerContact, VendorSummary


class ReportCreate(BaseModel):
    vendor_id: int | None = None
    review_id: int | None = None
    reason: ReportReason
    details: str | None = Field(default=None, max_length=2000)

    _details = field_validator("details")(clean_optional_text)

    @model_validator(mode="after")
    def exactly_one_target(self) -> "ReportCreate":
        if (self.vendor_id is None) == (self.review_id is None):
            raise ValueError("Report either a vendor or a review")
        return self


class ReportAck(BaseModel):
    id: int
    status: ReportStatus


class ReportResolve(BaseModel):
    status: Literal["resolved", "dismissed"]
    admin_notes: str | None = Field(default=None, max_length=2000)

    _notes = field_validator("admin_notes")(clean_optional_text)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reason: ReportReason
    details: str | None
    status: ReportStatus
    admin_notes: str | None
    created_at: datetime
    resolved_at: datetime | None
    reporter: CustomerContact | None
    vendor: VendorSummary | None
    review_id: int | None


class AuditActor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: int | None
    details: dict[str, Any]
    created_at: datetime
    actor: AuditActor | None
