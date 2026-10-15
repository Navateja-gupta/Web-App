from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import PasswordChange, TokenResponse, UserLogin, UserRead, UserRegister, UserUpdate
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

login_rate_limit = rate_limit(settings.LOGIN_RATE_LIMIT, settings.LOGIN_RATE_WINDOW_SECONDS)
register_rate_limit = rate_limit(settings.REGISTER_RATE_LIMIT, settings.REGISTER_RATE_WINDOW_SECONDS)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
)
def register(data: UserRegister, response: Response, db: Session = Depends(get_db)) -> User:
    """Create a customer or vendor account and log it in."""
    user = auth_service.register_user(db, data)
    access, refresh = auth_service.issue_session(db, user)
    set_auth_cookies(response, access, refresh)
    return user


@router.post("/login", response_model=UserRead, dependencies=[Depends(login_rate_limit)])
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)) -> User:
    """Browser login: tokens are set as HTTP-only cookies and never returned in the body."""
    user = auth_service.authenticate(db, data.email, data.password)
    access, refresh = auth_service.issue_session(db, user)
    set_auth_cookies(response, access, refresh)
    return user


@router.post("/token", response_model=TokenResponse, dependencies=[Depends(login_rate_limit)])
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """OAuth2 password flow for Swagger UI and Postman. Use the email as the username."""
    user = auth_service.authenticate(db, form.username, form.password)
    return TokenResponse(access_token=create_access_token(user.id, user.role.value))


@router.post("/refresh", response_model=UserRead)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    """Rotate the refresh-token cookie and issue a fresh access-token cookie."""
    user, access, new_refresh = auth_service.rotate_refresh_token(db, request.cookies.get(REFRESH_COOKIE))
    set_auth_cookies(response, access, new_refresh)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    auth_service.revoke_refresh_token(db, request.cookies.get(REFRESH_COOKIE))
    clear_auth_cookies(response)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserRead)
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    return auth_service.update_profile(db, user, data)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChange,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Change password, sign out all other sessions, and keep this browser signed in."""
    auth_service.change_password(db, user, data)
    access, refresh = auth_service.issue_session(db, user)
    set_auth_cookies(response, access, refresh)
