from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class TodoStatus(str, enum.Enum):
    draft = 'draft'
    approved = 'approved'
    rejected = 'rejected'
    done = 'done'


class Priority(str, enum.Enum):
    critical = 'critical'
    high = 'high'
    medium = 'medium'
    low = 'low'


class Todo(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'todos'

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    priority: Mapped[Priority] = mapped_column(
        Enum(Priority), nullable=False, default=Priority.medium
    )
    priority_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    blocker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_links: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [url, ...]
    source_snippets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    status: Mapped[TodoStatus] = mapped_column(
        Enum(TodoStatus), nullable=False, default=TodoStatus.draft
    )

    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    project: Mapped[Optional['Project']] = relationship('Project', back_populates='todos')  # type: ignore[name-defined]
