from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def get_by_id(db: Session, user_id) -> User | None:  # noqa: ANN001
    return db.get(User, user_id)


def create(db: Session, *, email: str, password_hash: str, display_name: str | None) -> User:
    user = User(
        email=normalize_email(email), password_hash=password_hash, display_name=display_name
    )
    db.add(user)
    db.flush()
    return user
