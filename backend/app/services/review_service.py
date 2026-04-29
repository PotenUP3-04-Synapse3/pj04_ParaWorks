"""Review service — accept/reject draft items in the review queue."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_item import ReviewItem, ReviewItemStatus, ReviewItemType
from app.models.todo import Todo, TodoStatus
from app.models.timeline import TimelineEvent, EventStatus
from app.models.history import HistoryEvent, HistoryStatus

logger = logging.getLogger(__name__)


async def accept_review_item(
    db: AsyncSession,
    item_id: UUID,
    reviewed_by: UUID,
) -> ReviewItem:
    """Approve a review item and update the underlying record to 'approved'."""
    item = await _get_item_or_raise(db, item_id)

    item.status = ReviewItemStatus.approved
    item.reviewed_by = reviewed_by
    from datetime import datetime, timezone
    item.reviewed_at = datetime.now(timezone.utc)

    await _update_source_record(db, item, approved=True)
    await db.commit()
    await db.refresh(item)
    return item


async def reject_review_item(
    db: AsyncSession,
    item_id: UUID,
    reviewed_by: UUID,
    rejection_reason: Optional[str] = None,
) -> ReviewItem:
    """Reject a review item and mark the underlying record as 'rejected'."""
    item = await _get_item_or_raise(db, item_id)

    item.status = ReviewItemStatus.rejected
    item.reviewed_by = reviewed_by
    item.rejection_reason = rejection_reason
    from datetime import datetime, timezone
    item.reviewed_at = datetime.now(timezone.utc)

    await _update_source_record(db, item, approved=False)
    await db.commit()
    await db.refresh(item)
    return item


async def _get_item_or_raise(db: AsyncSession, item_id: UUID) -> ReviewItem:
    result = await db.execute(select(ReviewItem).where(ReviewItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise ValueError(f'ReviewItem {item_id} not found')
    if item.status != ReviewItemStatus.pending:
        raise ValueError(f'ReviewItem {item_id} already processed: {item.status}')
    return item


async def _update_source_record(db: AsyncSession, item: ReviewItem, approved: bool) -> None:
    """Update the actual Todo / TimelineEvent / HistoryEvent record."""
    if item.item_type == ReviewItemType.todo:
        result = await db.execute(select(Todo).where(Todo.id == item.item_id))
        record = result.scalar_one_or_none()
        if record:
            record.status = TodoStatus.approved if approved else TodoStatus.rejected

    elif item.item_type == ReviewItemType.timeline_event:
        result = await db.execute(select(TimelineEvent).where(TimelineEvent.id == item.item_id))
        record = result.scalar_one_or_none()
        if record:
            record.status = EventStatus.approved if approved else EventStatus.rejected

    elif item.item_type == ReviewItemType.history_event:
        result = await db.execute(select(HistoryEvent).where(HistoryEvent.id == item.item_id))
        record = result.scalar_one_or_none()
        if record:
            record.status = HistoryStatus.approved if approved else HistoryStatus.rejected
