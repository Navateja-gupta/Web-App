import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id with pwdlib's recommended parameters.
_password_hash = PasswordHash.recommended()
_DUMMY_HASH = _password_hash.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    """Return (is_valid, upgraded_hash). upgraded_hash is set when hashing parameters changed."""
    return _password_hash.verify_and_update(password, password_hash)


def spend_password_check_time(password: str) -> None:
    """Run a hash check against a dummy hash so unknown emails take as long as wrong passwords."""
    _password_hash.verify(password, _DUMMY_HASH)


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
