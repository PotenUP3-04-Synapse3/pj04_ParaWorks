"""Admin API — user management, permission policies, and audit log access."""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.permission_policy import AccessLevel, PermissionPolicy
from app.models.user import User, UserRole

router = APIRouter(prefix='/admin', tags=['admin'])
logger = logging.getLogger(__name__)


# ── Guards ────────────────────────────────────────────────────────────────

async def _require_admin(request: Request, db: AsyncSession) -> User:
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Admin role required',
        )
    return user


# ── User management ───────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    is_active: bool
    department_id: Optional[UUID]
    team_id: Optional[UUID]

    model_config = {'from_attributes': True}


class UserRoleUpdateBody(BaseModel):
    role: UserRole
    is_active: Optional[bool] = None
    department_id: Optional[UUID] = None
    team_id: Optional[UUID] = None


@router.get('/users', response_model=List[UserOut])
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> List[UserOut]:
    await _require_admin(request, db)
    org_id = request.state.org_id

    q = select(User).where(User.organization_id == org_id).offset(skip).limit(limit)
    if role:
        q = q.where(User.role == role)
    if is_active is not None:
        q = q.where(User.is_active == is_active)

    rows = (await db.execute(q)).scalars().all()
    return [UserOut.model_validate(u) for u in rows]


@router.patch('/users/{user_id}', response_model=UserOut)
async def update_user(
    user_id: UUID,
    body: UserRoleUpdateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    admin = await _require_admin(request, db)
    org_id = request.state.org_id

    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.department_id is not None:
        user.department_id = body.department_id
    if body.team_id is not None:
        user.team_id = body.team_id

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ── Permission policies ───────────────────────────────────────────────────

class PermissionPolicyOut(BaseModel):
    id: UUID
    role: str
    resource_type: str
    access_level: str

    model_config = {'from_attributes': True}


class PermissionPolicyUpdateBody(BaseModel):
    access_level: AccessLevel


@router.get('/permissions', response_model=List[PermissionPolicyOut])
async def list_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> List[PermissionPolicyOut]:
    await _require_admin(request, db)
    org_id = request.state.org_id

    rows = (
        await db.execute(
            select(PermissionPolicy).where(PermissionPolicy.organization_id == org_id)
        )
    ).scalars().all()
    return [PermissionPolicyOut.model_validate(r) for r in rows]


@router.patch('/permissions/{policy_id}', response_model=PermissionPolicyOut)
async def update_permission(
    policy_id: UUID,
    body: PermissionPolicyUpdateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PermissionPolicyOut:
    await _require_admin(request, db)
    org_id = request.state.org_id

    result = await db.execute(
        select(PermissionPolicy).where(
            PermissionPolicy.id == policy_id,
            PermissionPolicy.organization_id == org_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    policy.access_level = body.access_level
    await db.commit()
    await db.refresh(policy)
    return PermissionPolicyOut.model_validate(policy)


# ── Audit logs ────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_path: Optional[str]
    ip_addr: Optional[str]
    status_code: Optional[int]
    created_at: object  # datetime

    model_config = {'from_attributes': True}


@router.get('/audit-logs', response_model=List[AuditLogOut])
async def list_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> List[AuditLogOut]:
    await _require_admin(request, db)

    q = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if action:
        q = q.where(AuditLog.action.ilike(f'%{action}%'))

    rows = (await db.execute(q)).scalars().all()
    return [AuditLogOut.model_validate(r) for r in rows]
