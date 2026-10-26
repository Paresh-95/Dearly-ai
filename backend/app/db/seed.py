from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import User


async def ensure_admin_user(db: AsyncSession) -> None:
    """Keep the single admin account in sync with ADMIN_EMAIL / ADMIN_PASSWORD.

    Admin access is not something a signup can acquire — it's one fixed
    account whose credentials live in the environment, created on first
    startup and kept in sync (password + flags) on every later one so
    rotating the env values is enough to rotate the login.
    """
    email = settings.admin_email.lower()
    result = await db.execute(select(User).where(User.email == email))
    admin = result.scalar_one_or_none()

    if admin is None:
        db.add(
            User(
                email=email,
                password_hash=hash_password(settings.admin_password),
                is_approved=True,
                is_admin=True,
            )
        )
    else:
        admin.password_hash = hash_password(settings.admin_password)
        admin.is_approved = True
        admin.is_admin = True

    # Enforce a single admin: demote any other account that was promoted
    # under the old first-signup-becomes-admin behavior.
    other_admins = await db.execute(select(User).where(User.is_admin.is_(True), User.email != email))
    for stale_admin in other_admins.scalars().all():
        stale_admin.is_admin = False

    await db.commit()
