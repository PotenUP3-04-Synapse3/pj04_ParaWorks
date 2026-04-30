"""Decisions API — DecisionRecord CRUD + approval flow."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.decision_record import (
    DecisionRecord,
    DecisionPermissionLevel,
    DecisionReviewStatus,
)
from app.models.user import User, UserRole

router = APIRouter(prefix='/decisions', tags=['decisions'])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ──────────────────────────────────────────────────────

class DecisionOut(BaseModel):
    id: UUID
    title: str
    decision_summary: Optional[str]
    situation: Optional[str]
    reason: Optional[str]
    alternatives_considered: Optional[list]
    constraints: Optional[str]
    final_decision: Optional[str]
    decision_maker: Optional[str]
    participants: Optional[list]
    decided_at: Optional[datetime]
    confidence_score: Optional[float]
    permission_level: str
    review_status: str
    source_links: Optional[list]
    source_snippets: Optional[list]
    tags: Optional[list]
    business_domain: Optional[str]
    related_project_id: Optional[UUID]
    organization_id: UUID
    created_at: datetime

    model_config = {'from_attributes': True}


class DecisionListOut(BaseModel):
    id: UUID
    title: str
    decision_summary: Optional[str]
    business_domain: Optional[str]
    decided_at: Optional[datetime]
    confidence_score: Optional[float]
    review_status: str
    permission_level: str

    model_config = {'from_attributes': True}


class DecisionRejectBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class DecisionCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    decision_summary: Optional[str] = None
    situation: Optional[str] = None
    reason: Optional[str] = None
    alternatives_considered: Optional[list] = None
    constraints: Optional[str] = None
    final_decision: Optional[str] = None
    decision_maker: Optional[str] = None
    participants: Optional[list] = None
    decided_at: Optional[datetime] = None
    permission_level: DecisionPermissionLevel = DecisionPermissionLevel.team
    business_domain: Optional[str] = None
    tags: Optional[list] = None
    related_project_id: Optional[UUID] = None


# ── Helpers ───────────────────────────────────────────────────────────────

async def _require_user(request: Request, db: AsyncSession) -> User:
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


def _allowed_levels(role: UserRole) -> List[str]:
    if role in (UserRole.admin, UserRole.manager):
        return ['public', 'team', 'restricted']
    return ['public', 'team']


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get('', response_model=List[DecisionListOut])
async def list_decisions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    review_status: Optional[str] = Query(None),
    business_domain: Optional[str] = Query(None),
    project_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> List[DecisionListOut]:
    user = await _require_user(request, db)
    org_id = request.state.org_id
    allowed = _allowed_levels(user.role)

    q = (
        select(DecisionRecord)
        .where(
            DecisionRecord.organization_id == org_id,
            DecisionRecord.permission_level.in_(allowed),
        )
        .order_by(DecisionRecord.decided_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    if review_status:
        q = q.where(DecisionRecord.review_status == review_status)
    if business_domain:
        q = q.where(DecisionRecord.business_domain == business_domain)
    if project_id:
        q = q.where(DecisionRecord.related_project_id == project_id)

    rows = (await db.execute(q)).scalars().all()
    return [DecisionListOut.model_validate(r) for r in rows]


@router.get('/{decision_id}', response_model=DecisionOut)
async def get_decision(
    decision_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DecisionOut:
    user = await _require_user(request, db)
    org_id = request.state.org_id
    allowed = _allowed_levels(user.role)

    result = await db.execute(
        select(DecisionRecord).where(
            DecisionRecord.id == decision_id,
            DecisionRecord.organization_id == org_id,
            DecisionRecord.permission_level.in_(allowed),
        )
    )
    dr = result.scalar_one_or_none()
    if not dr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Decision not found')
    return DecisionOut.model_validate(dr)


@router.post('', response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
async def create_decision(
    body: DecisionCreateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DecisionOut:
    user = await _require_user(request, db)
    org_id = request.state.org_id

    dr = DecisionRecord(
        organization_id=org_id,
        **body.model_dump(exclude_none=True),
        review_status=DecisionReviewStatus.draft,
    )
    db.add(dr)
    await db.commit()
    await db.refresh(dr)
    return DecisionOut.model_validate(dr)


@router.post('/{decision_id}/approve', response_model=DecisionOut)
async def approve_decision(
    decision_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DecisionOut:
    user = await _require_user(request, db)
    if user.role not in (UserRole.admin, UserRole.manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role')

    org_id = request.state.org_id
    result = await db.execute(
        select(DecisionRecord).where(
            DecisionRecord.id == decision_id,
            DecisionRecord.organization_id == org_id,
        )
    )
    dr = result.scalar_one_or_none()
    if not dr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    dr.review_status = DecisionReviewStatus.approved
    await db.commit()
    await db.refresh(dr)
    return DecisionOut.model_validate(dr)


@router.post('/{decision_id}/reject', response_model=DecisionOut)
async def reject_decision(
    decision_id: UUID,
    body: DecisionRejectBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DecisionOut:
    user = await _require_user(request, db)
    if user.role not in (UserRole.admin, UserRole.manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role')

    org_id = request.state.org_id
    result = await db.execute(
        select(DecisionRecord).where(
            DecisionRecord.id == decision_id,
            DecisionRecord.organization_id == org_id,
        )
    )
    dr = result.scalar_one_or_none()
    if not dr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    dr.review_status = DecisionReviewStatus.rejected
    # Store rejection reason in source_links (simple approach)
    notes = dr.source_links or []
    notes.append({'rejection_reason': body.reason, 'rejected_by': str(user.id)})
    dr.source_links = notes

    await db.commit()
    await db.refresh(dr)
    return DecisionOut.model_validate(dr)
