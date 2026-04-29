from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class EventStatus(str, enum.Enum):
    draft = 'draft'
    approved = 'approved'
    rejected = 'rejected'


class TimelineEvent(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'timeline_events'

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    event_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    source_links: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    source_snippets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), nullable=False, default=EventStatus.draft
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    project: Mapped['Project'] = relationship('Project', back_populates='timeline_events')  # type: ignore[name-defined]
