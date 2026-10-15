import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole

_INDIAN_MOBILE = re.compile(r"^(?:\+?91)?([6-9]\d{9})$")


def normalize_phone(value: str | None) -> str | None:
    """Accept common Indian mobile formats and store as +91XXXXXXXXXX."""
    if value is None:
        return None
    compact = re.sub(r"[\s\-()]", "", value)
    if not compact:
        return None
    match = _INDIAN_MOBILE.match(compact)
    if not match:
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return f"+91{match.group(1)}"


def check_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


def clean_name(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("Name must be at least 2 characters")
    return value


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)
    # Administrators cannot self-register; they are created with the CLI script.
    role: Literal["customer", "vendor"] = "customer"

    _clean_name = field_validator("full_name")(clean_name)
    _normalize_phone = field_validator("phone")(normalize_phone)
    _password_strength = field_validator("password")(check_password_strength)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    email_notifications: bool | None = None

    _clean_name = field_validator("full_name")(lambda v: clean_name(v) if v is not None else v)
    _normalize_phone = field_validator("phone")(normalize_phone)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    _password_strength = field_validator("new_password")(check_password_strength)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    role: UserRole
    is_active: bool
    email_notifications: bool
    created_at: datetime


class UserStatusUpdate(BaseModel):
    is_active: bool


class ResetLinkRead(BaseModel):
    reset_url: str
    expires_at: datetime
    user_email: str


class ResetTokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResetTokenInfo(BaseModel):
    first_name: str


class PasswordResetConfirm(ResetTokenIn):
    new_password: str = Field(min_length=8, max_length=128)

    _password_strength = field_validator("new_password")(check_password_strength)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
