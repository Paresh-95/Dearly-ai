from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import NotFound, Unauthenticated
from app.core.security import decode_token
from app.db.session import get_db
from app.models import PersonProfile, User
from app.repositories import profiles as profile_repo
from app.repositories import users as user_repo

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


@dataclass(frozen=True)
class AuthContext:
    """Identity every repository call is scoped by."""

    user_id: UUID


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise Unauthenticated("Authentication required")
    user_id = decode_token(credentials.credentials, "access")
    user = user_repo.get_by_id(db, user_id) if user_id else None
    if user is None or not user.is_active:
        raise Unauthenticated("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_auth_context(user: CurrentUser) -> AuthContext:
    return AuthContext(user_id=user.id)


Auth = Annotated[AuthContext, Depends(get_auth_context)]


def get_owned_profile(profile_id: UUID, db: DbSession, auth: Auth) -> PersonProfile:
    profile = profile_repo.get_owned(db, auth.user_id, profile_id)
    if profile is None:
        raise NotFound("Profile not found")
    return profile


OwnedProfile = Annotated[PersonProfile, Depends(get_owned_profile)]
