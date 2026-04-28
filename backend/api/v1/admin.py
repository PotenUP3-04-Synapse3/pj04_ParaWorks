from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from backend.core.dependencies import CurrentUserId, DbSession
from backend.core.permissions import UserRole
from backend.models.audit_log import AuditLog
from backend.models.user import User
from backend.schemas.admin import AuditLogRead
from backend.schemas.auth import UserRead

log = structlog.get_logger(__name__)
router = APIRouter(prefix='/admin', tags=['admin'])


async def _require_admin(user_id: CurrentUserId, db: DbSession) -> User:
    user = await db.get(User, user_id)
    if not user or user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='관리자 권한이 필요합니다')
    return user


class RoleUpdate(BaseModel := __import__('pydantic').BaseModel):
    role: str
    department_id: str | None = None
    team_id: str | None = None


@router.get('/users', response_model=list[UserRead])
async def list_users(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    await _require_admin(user_id, db)
    result = await db.execute(
        select(User)
        .where(User.organization_id == org_id)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.patch('/users/{target_user_id}', response_model=UserRead)
async def update_user_role(
    target_user_id: str,
    payload: RoleUpdate,
    db: DbSession,
    user_id: CurrentUserId,
):
    actor = await _require_admin(user_id, db)
    target = await db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    valid_roles = {r.value for r in UserRole}
    if payload.role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'유효하지 않은 역할: {payload.role}')

    target.role = payload.role
    if payload.department_id is not None:
        target.department_id = payload.department_id
    if payload.team_id is not None:
        target.team_id = payload.team_id

    import uuid
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=actor.organization_id,
        actor_id=user_id,
        actor_email=actor.email,
        action='user.role_change',
        resource_type='user',
        resource_id=target_user_id,
        detail=f'역할 변경: {payload.role}',
    ))
    await db.commit()
    await db.refresh(target)
    return target


@router.get('/audit-logs', response_model=list[AuditLogRead])
async def get_audit_logs(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    await _require_admin(user_id, db)
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
