"""Audit log routes (admin only)."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import UserRole

router = APIRouter(prefix='/audit-logs', tags=['audit-logs'])


class AuditLogOut(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_path: Optional[str]
    ip_addr: Optional[str]
    status_code: Optional[int]

    model_config = {'from_attributes': True}


@router.get('', response_model=List[AuditLogOut])
async def list_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    # Admin-only
    if request.state.role not in (UserRole.admin.value, 'admin'):
        raise HTTPException(status_code=403, detail='Admin only')

    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()
