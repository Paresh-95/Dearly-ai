from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKeyConstraint


def enum_check(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    values = ", ".join(f"'{m.value}'" for m in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or f"{column}_valid")


def profile_fk() -> ForeignKeyConstraint:
    """Tie (person_profile_id, user_id) to a profile so a row can never name a profile
    owned by a different user."""
    return ForeignKeyConstraint(
        ["person_profile_id", "user_id"],
        ["person_profiles.id", "person_profiles.user_id"],
        ondelete="CASCADE",
    )
