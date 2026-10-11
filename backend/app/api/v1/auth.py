from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import Conflict, Unauthenticated
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.repositories import users as user_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the email is unknown so response time doesn't reveal accounts.
_DUMMY_HASH = hash_password("not-a-real-password")


def _set_refresh_cookie(response: Response, user_id) -> None:  # noqa: ANN001
    s = get_settings()
    response.set_cookie(
        s.refresh_cookie_name,
        create_token(user_id, "refresh"),
        max_age=s.refresh_token_days * 86400,
        httponly=True,
        secure=s.refresh_cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
def register(body: RegisterRequest, response: Response, db: DbSession) -> TokenResponse:
    if user_repo.get_by_email(db, body.email):
        raise Conflict("An account with this email already exists")
    try:
        user = user_repo.create(
            db,
            email=body.email,
            password_hash=hash_password(body.password),
            display_name=body.display_name,
        )
        db.commit()
    except IntegrityError:  # concurrent registration race
        db.rollback()
        raise Conflict("An account with this email already exists") from None
    _set_refresh_cookie(response, user.id)
    return TokenResponse(access_token=create_token(user.id, "access"))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    user = user_repo.get_by_email(db, body.email)
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok or not user.is_active:
        raise Unauthenticated("Incorrect email or password")
    _set_refresh_cookie(response, user.id)
    return TokenResponse(access_token=create_token(user.id, "access"))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: DbSession,
    mc_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    user_id = decode_token(mc_refresh, "refresh") if mc_refresh else None
    user = user_repo.get_by_id(db, user_id) if user_id else None
    if user is None or not user.is_active:
        raise Unauthenticated("Session expired")
    _set_refresh_cookie(response, user.id)
    return TokenResponse(access_token=create_token(user.id, "access"))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(get_settings().refresh_cookie_name, path="/api/v1/auth")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
