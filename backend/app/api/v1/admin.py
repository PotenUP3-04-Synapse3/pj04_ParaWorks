from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, find_demo_user, require_admin_user
from backend.app.core.rbac import (
    validate_permission_levels,
    validate_role,
    validate_status,
)
from backend.app.core.session_auth import (
    serialize_auth_user,
    upsert_auth_user_from_demo,
)
from backend.app.db.session import get_db
from backend.app.models import AuditLog, AuthUser
from backend.app.seeds.auth_users import seed_auth_users
from backend.app.services.audit import record_audit_log, serialize_audit_log

router = APIRouter(prefix='/admin', tags=['admin'])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]


class AdminUserUpdate(BaseModel):
    role: str | None = None
    status: str | None = None
    department: str | None = None
    title: str | None = None
    permission_levels: list[str] | None = None


@router.get('/audit-logs')
def list_audit_logs(db: DbSession, _: AdminUser, limit: int = 50) -> dict[str, list[dict[str, object]]]:
    safe_limit = max(1, min(limit, 100))
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(safe_limit)).all()
    return {'logs': [serialize_audit_log(log) for log in logs]}


@router.get('/users')
def list_admin_users(db: DbSession, _: AdminUser) -> dict[str, list[dict[str, object]]]:
    _ensure_seed_auth_users(db)
    db.commit()
    users = db.scalars(select(AuthUser).order_by(AuthUser.role, AuthUser.email)).all()
    return {'users': [serialize_auth_user(user) for user in users]}


@router.patch('/users/{external_id}')
def update_admin_user(
    external_id: str,
    update: AdminUserUpdate,
    db: DbSession,
    admin_user: AdminUser,
) -> dict[str, dict[str, object]]:
    target_user = _get_or_seed_auth_user(db, external_id)
    previous = _managed_user_snapshot(target_user)
    update_payload = update.model_dump(exclude_unset=True)

    if 'role' in update_payload and update.role is not None:
        target_user.role = validate_role(update.role)
    if 'status' in update_payload and update.status is not None:
        target_user.status = validate_status(update.status)
    if 'department' in update_payload and update.department is not None:
        target_user.department = update.department.strip()
    if 'title' in update_payload and update.title is not None:
        target_user.title = update.title.strip()
    if 'permission_levels' in update_payload and update.permission_levels is not None:
        target_user.permission_levels = validate_permission_levels(update.permission_levels)

    next_values = _managed_user_snapshot(target_user)
    record_audit_log(
        db=db,
        actor=admin_user,
        action='admin.user.update',
        target_type='auth_user',
        target_id=target_user.external_id,
        metadata={
            'previous': previous,
            'next': next_values,
            'changed_fields': sorted(update_payload),
        },
    )
    db.commit()
    db.refresh(target_user)
    return {'user': serialize_auth_user(target_user)}


def _ensure_seed_auth_users(db: Session) -> None:
    seed_auth_users(db)


def _get_or_seed_auth_user(db: Session, external_id: str) -> AuthUser:
    target_user = db.scalar(select(AuthUser).where(AuthUser.external_id == external_id))
    if target_user is not None:
        return target_user

    seed_user = find_demo_user(external_id)
    if seed_user is not None:
        return upsert_auth_user_from_demo(db, seed_user)

    raise HTTPException(status_code=404, detail='User not found.')


def _managed_user_snapshot(user: AuthUser) -> dict[str, object]:
    return {
        'external_id': user.external_id,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'department': user.department,
        'title': user.title,
        'permission_levels': sorted(user.permission_levels),
    }
