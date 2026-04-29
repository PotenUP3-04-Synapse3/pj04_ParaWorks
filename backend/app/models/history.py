from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class HistoryStatus(str, enum.Enum):
    draft = 'draft'
    approved = 'approved'
    rejected = 'rejected'


class HistoryEvent(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'history_events'

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    situation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_maker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    participants: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [email, ...]

    source_links: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    source_snippets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[HistoryStatus] = mapped_column(
        Enum(HistoryStatus), nullable=False, default=HistoryStatus.draft
    )

    event_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    project: Mapped['Project'] = relationship('Project', back_populates='history_events')  # type: ignore[name-defined]
