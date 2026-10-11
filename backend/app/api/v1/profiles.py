from fastapi import APIRouter, status

from app.api.deps import Auth, DbSession, OwnedProfile
from app.repositories import profiles as repo
from app.schemas.profile import ProfileCreate, ProfileList, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileRead)
def create_profile(body: ProfileCreate, db: DbSession, auth: Auth) -> ProfileRead:
    profile = repo.create(db, auth.user_id, body)
    db.commit()
    return ProfileRead.model_validate(profile)


@router.get("", response_model=ProfileList)
def list_profiles(db: DbSession, auth: Auth) -> ProfileList:
    items = repo.list_for_user(db, auth.user_id)
    return ProfileList(items=[ProfileRead.model_validate(p) for p in items])


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile: OwnedProfile) -> ProfileRead:
    return ProfileRead.model_validate(profile)


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(profile: OwnedProfile, body: ProfileUpdate, db: DbSession) -> ProfileRead:
    repo.update(db, profile, body)
    db.commit()
    return ProfileRead.model_validate(profile)
