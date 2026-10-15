from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cookies import ACCESS_COOKIE
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

# Lets Swagger's "Authorize" button and Postman use a bearer token.
# auto_error=False because browsers authenticate with the HTTP-only cookie instead.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token", auto_error=False)


def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = bearer_token or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise AuthenticationError("Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise AuthenticationError("Invalid or expired token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise AuthenticationError("Invalid or expired token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid or expired token")
    # Reject tokens issued before a password change / deactivation (whole-second precision, like iat).
    if user.tokens_valid_after is not None and int(payload["iat"]) < int(user.tokens_valid_after.timestamp()):
        raise AuthenticationError("Invalid or expired token")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Dependency factory: allow only users whose role is in `roles`."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("You do not have permission to perform this action")
        return user

    return dependency


require_admin = require_roles(UserRole.ADMIN)
require_vendor = require_roles(UserRole.VENDOR)
require_customer = require_roles(UserRole.CUSTOMER)
