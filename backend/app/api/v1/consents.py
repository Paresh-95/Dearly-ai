from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import Auth, DbSession
from app.core.errors import NotFound
from app.repositories import consents as repo
from app.repositories import profiles as profile_repo
from app.schemas.consent import ConsentCreate, ConsentList, ConsentRead

router = APIRouter(prefix="/consents", tags=["consents"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConsentRead)
def create_consent(body: ConsentCreate, db: DbSession, auth: Auth) -> ConsentRead:
    if body.person_profile_id is not None:
        if profile_repo.get_owned(db, auth.user_id, body.person_profile_id) is None:
            raise NotFound("Profile not found")
    record = repo.create(db, auth.user_id, body)
    db.commit()
    return ConsentRead.model_validate(record)


@router.get("", response_model=ConsentList)
def list_consents(
    db: DbSession, auth: Auth, person_profile_id: UUID | None = None
) -> ConsentList:
    items = repo.list_for_user(db, auth.user_id, person_profile_id=person_profile_id)
    return ConsentList(items=[ConsentRead.model_validate(c) for c in items])
