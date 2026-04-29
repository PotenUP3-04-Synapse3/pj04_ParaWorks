"""Notification Agent — evaluates conditions and fires notifications."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.todo import Todo, TodoStatus

logger = logging.getLogger(__name__)

DEADLINE_ALERT_DAYS = 3


async def run_notification_agent(
    db: AsyncSession,
    todos: List[Todo],
    user_id: UUID,
) -> List[Notification]:
    """Evaluate todos and create notifications for actionable conditions."""
    notifications: List[Notification] = []
    today = date.today()

    for todo in todos:
        if todo.status != TodoStatus.approved:
            continue

        # Deadline approaching
        if todo.due_date and (todo.due_date - today).days <= DEADLINE_ALERT_DAYS:
            notifications.append(
                Notification(
                    user_id=user_id,
                    notification_type=NotificationType.deadline_approaching,
                    title=f'마감 임박: {todo.title}',
                    message=f'{todo.due_date} 마감 예정입니다.',
                    source_link=(todo.source_links or [None])[0],
                )
            )

        # Blocker detected
        if todo.blocker:
            notifications.append(
                Notification(
                    user_id=user_id,
                    notification_type=NotificationType.blocker_detected,
                    title=f'Blocker 발생: {todo.title}',
                    message='이 태스크가 다른 작업을 차단하고 있습니다.',
                    source_link=(todo.source_links or [None])[0],
                )
            )

        # Approval needed
        if todo.needs_approval:
            notifications.append(
                Notification(
                    user_id=user_id,
                    notification_type=NotificationType.approval_needed,
                    title=f'승인 필요: {todo.title}',
                    message='의사결정권자의 승인이 필요합니다.',
                    source_link=(todo.source_links or [None])[0],
                )
            )

    for n in notifications:
        db.add(n)

    return notifications
