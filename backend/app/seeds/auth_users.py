from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import USERS
from backend.app.models import AuthUser, RefreshToken

REMOVED_SEED_EMAILS = {
    'jun@paraworks.com',
    'soyeon@paraworks.com',
}


def seed_auth_users(db: Session) -> list[AuthUser]:
    removed_users = db.scalars(select(AuthUser).where(AuthUser.email.in_(REMOVED_SEED_EMAILS))).all()
    if removed_users:
        removed_user_ids = [user.id for user in removed_users]
        db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(removed_user_ids)))
        for removed_user in removed_users:
            db.delete(removed_user)
        db.flush()

    seeded_users: list[AuthUser] = []
    for seed_user in USERS.values():
        existing = db.scalar(
            select(AuthUser).where(
                or_(
                    AuthUser.email == seed_user.email,
                    AuthUser.external_id == seed_user.id,
                )
            )
        )
        if existing is not None:
            seeded_users.append(existing)
            continue

        auth_user = AuthUser(
            external_id=seed_user.id,
            email=seed_user.email,
            display_name=seed_user.name,
            role=seed_user.role,
            department=seed_user.department,
            title=seed_user.title,
            status='active',
            permission_levels=sorted(seed_user.permission_levels),
        )
        db.add(auth_user)
        seeded_users.append(auth_user)
    db.flush()
    return seeded_users
