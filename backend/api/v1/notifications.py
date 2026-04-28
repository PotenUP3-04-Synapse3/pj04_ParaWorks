from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.notification import Notification
from backend.schemas.admin import NotificationRead

log = structlog.get_logger(__name__)
router = APIRouter(prefix='/notifications', tags=['notifications'])


@router.get('', response_model=list[NotificationRead])
async def list_notifications(
    db: DbSession,
    user_id: CurrentUserId,
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)
    q = q.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()


@router.patch('/{notification_id}/read', response_model=NotificationRead)
async def mark_read(notification_id: str, db: DbSession, user_id: CurrentUserId):
    notif = await db.get(Notification, notification_id)
    if not notif or notif.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return notif


@router.post('/read-all')
async def mark_all_read(db: DbSession, user_id: CurrentUserId):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {'status': 'ok'}
