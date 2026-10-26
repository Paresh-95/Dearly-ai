import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import AUTH_COOKIE_NAME, get_current_admin, get_current_user
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, validate_password_strength, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    is_admin: bool
    is_approved: bool

    class Config:
        from_attributes = True


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
    )


@router.post("/signup", status_code=201)
async def signup(
    payload: SignupIn,
    db: AsyncSession = Depends(get_db),
    _rate_limited: None = Depends(rate_limit(5)),
) -> dict:
    strength_error = validate_password_strength(payload.password)
    if strength_error:
        raise HTTPException(status_code=400, detail=strength_error)

    email = payload.email.lower()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="An account with that email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        is_approved=False,
        is_admin=False,
    )
    db.add(user)
    await db.commit()

    return {"message": "Account created. An admin needs to approve it before you can log in."}


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rate_limited: None = Depends(rate_limit(5)),
) -> User:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="That email and password don't match what we have. Double-check and try again.")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Your account is still waiting for admin approval.")

    token = create_access_token(str(user.id))
    _set_auth_cookie(response, token)
    return user


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return {"message": "Logged out."}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/pending-users", response_model=list[UserOut])
async def list_pending_users(
    db: AsyncSession = Depends(get_db), _admin: User = Depends(get_current_admin)
) -> list[User]:
    result = await db.execute(select(User).where(User.is_approved.is_(False)).order_by(User.created_at))
    return list(result.scalars().all())


@router.post("/approve/{user_id}", response_model=UserOut)
async def approve_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _admin: User = Depends(get_current_admin)
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_approved = True
    await db.commit()
    await db.refresh(user)
    return user
