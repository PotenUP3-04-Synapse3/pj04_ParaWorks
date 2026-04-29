"""Notifications routes."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.notification import Notification

router = APIRouter(prefix='/notifications', tags=['notifications'])


class NotificationOut(BaseModel):
    id: UUID
    notification_type: str
    title: str
    message: Optional[str]
    source_link: Optional[str]
    is_read: bool

    model_config = {'from_attributes': True}


@router.get('', response_model=List[NotificationOut])
async def list_notifications(
    request: Request,
    db: AsyncSession = Depends(get_db),
    unread_only: bool = False,
):
    user_id = request.state.user_id
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    result = await db.execute(query.order_by(Notification.created_at.desc()))
    return result.scalars().all()


@router.post('/{notification_id}/read')
async def mark_read(
    notification_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    await db.commit()
    return {'status': 'ok'}


@router.post('/read-all')
async def mark_all_read(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {'status': 'ok'}
