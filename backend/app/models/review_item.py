from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class ReviewItemType(str, enum.Enum):
    todo = 'todo'
    timeline_event = 'timeline_event'
    history_event = 'history_event'
    project = 'project'
    decision_record = 'decision_record'
    slack_thread_summary = 'slack_thread_summary'


class ReviewItemStatus(str, enum.Enum):
    draft = 'draft'
    pending_review = 'pending_review'
    approved = 'approved'
    rejected = 'rejected'
    needs_more_evidence = 'needs_more_evidence'
    archived = 'archived'


class ReviewItem(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'review_items'

    item_type: Mapped[ReviewItemType] = mapped_column(Enum(ReviewItemType), nullable=False)

    # Polymorphic FK: points to the actual item UUID
    item_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    # Snapshot of the AI-generated content at creation time (for display)
    content_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob

    status: Mapped[ReviewItemStatus] = mapped_column(
        Enum(ReviewItemStatus), nullable=False, default=ReviewItemStatus.draft
    )

    created_by_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
