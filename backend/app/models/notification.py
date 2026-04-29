from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class NotificationType(str, enum.Enum):
    deadline_approaching = 'deadline_approaching'
    blocker_detected = 'blocker_detected'
    approval_needed = 'approval_needed'
    customer_report_needed = 'customer_report_needed'
    document_changed = 'document_changed'
    schedule_changed = 'schedule_changed'
    slack_mention = 'slack_mention'
    review_ready = 'review_ready'


class Notification(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'notifications'

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_link: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped['User'] = relationship('User', back_populates='notifications')  # type: ignore[name-defined]
