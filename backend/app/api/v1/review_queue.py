"""Review queue API — list pending items, accept, and reject."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.review_item import ReviewItem, ReviewItemStatus
from app.services.review_service import accept_review_item, reject_review_item

router = APIRouter(prefix='/review-queue', tags=['review-queue'])


class ReviewItemOut(BaseModel):
    id: UUID
    item_type: str
    status: str
    content_snapshot: Optional[dict]
    created_by_agent: Optional[str]
    reviewed_by: Optional[UUID]
    rejection_reason: Optional[str]

    model_config = {'from_attributes': True}


class RejectBody(BaseModel):
    reason: Optional[str] = None


@router.get('', response_model=List[ReviewItemOut])
async def list_review_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
    item_status: str = 'pending',
):
    org_id = request.state.org_id
    result = await db.execute(
        select(ReviewItem)
        .where(
            ReviewItem.organization_id == org_id,
            ReviewItem.status == ReviewItemStatus(item_status),
        )
        .order_by(ReviewItem.created_at.asc())
    )
    return result.scalars().all()


@router.post('/{item_id}/accept', response_model=ReviewItemOut)
async def accept_item(
    item_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = UUID(request.state.user_id)
    try:
        item = await accept_review_item(db, item_id=item_id, reviewed_by=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return item


@router.post('/{item_id}/reject', response_model=ReviewItemOut)
async def reject_item(
    item_id: UUID,
    body: RejectBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = UUID(request.state.user_id)
    try:
        item = await reject_review_item(
            db, item_id=item_id, reviewed_by=user_id, rejection_reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return item
