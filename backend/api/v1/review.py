from __future__ import annotations

"""리뷰 큐 — AI 추출 레코드(review_status=pending) 관리.
approve: pending → confirmed
reject: pending → rejected
edit: 필드 수정 후 confirmed
"""

import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.audit_log import AuditLog
from backend.models.decision_record import DecisionRecord
from backend.schemas.decision import DecisionRecordRead, DecisionRecordUpdate

log = structlog.get_logger(__name__)
router = APIRouter(prefix='/review', tags=['review'])


@router.get('', response_model=list[DecisionRecordRead])
async def list_review_queue(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    review_status: str = Query('pending'),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """리뷰 대기 의사결정 레코드 목록."""
    result = await db.execute(
        select(DecisionRecord)
        .where(
            DecisionRecord.organization_id == org_id,
            DecisionRecord.review_status == review_status,
        )
        .order_by(DecisionRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def _log_review_action(db: DbSession, org_id: str, actor_id: str, action: str, resource_id: str, detail: str):
    log_entry = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        actor_id=actor_id,
        action=action,
        resource_type='decision_record',
        resource_id=resource_id,
        detail=detail,
    )
    db.add(log_entry)


@router.post('/{item_id}/approve', response_model=DecisionRecordRead)
async def approve_review(item_id: str, db: DbSession, user_id: CurrentUserId):
    record = await db.get(DecisionRecord, item_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if record.review_status != 'pending':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='이미 처리된 레코드입니다')

    record.review_status = 'confirmed'
    await _log_review_action(db, record.organization_id, user_id, 'review.approve', item_id, '리뷰 승인')
    await db.commit()
    await db.refresh(record)
    log.info('review.approved', item_id=item_id, user_id=user_id)
    return record


@router.post('/{item_id}/reject', response_model=DecisionRecordRead)
async def reject_review(item_id: str, db: DbSession, user_id: CurrentUserId):
    record = await db.get(DecisionRecord, item_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if record.review_status != 'pending':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='이미 처리된 레코드입니다')

    record.review_status = 'rejected'
    await _log_review_action(db, record.organization_id, user_id, 'review.reject', item_id, '리뷰 거부')
    await db.commit()
    await db.refresh(record)
    log.info('review.rejected', item_id=item_id, user_id=user_id)
    return record


@router.patch('/{item_id}', response_model=DecisionRecordRead)
async def edit_and_approve(item_id: str, payload: DecisionRecordUpdate, db: DbSession, user_id: CurrentUserId):
    """편집 후 자동 승인."""
    record = await db.get(DecisionRecord, item_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(record, field, value)
    record.review_status = 'confirmed'

    await _log_review_action(db, record.organization_id, user_id, 'review.edit_approve', item_id, '편집 후 승인')
    await db.commit()
    await db.refresh(record)
    return record
