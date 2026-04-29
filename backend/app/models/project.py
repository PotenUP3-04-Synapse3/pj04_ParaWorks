from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.todo import Todo
    from app.models.timeline import TimelineEvent
    from app.models.history import HistoryEvent
    from app.models.source import Source


class RiskLevel(str, enum.Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'


class ProjectStatus(str, enum.Enum):
    draft = 'draft'
    active = 'active'
    on_hold = 'on_hold'
    completed = 'completed'
    cancelled = 'cancelled'


class Campaign(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'campaigns'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    projects: Mapped[List['Project']] = relationship('Project', back_populates='campaign')


class Project(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'projects'

    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), nullable=False, default=ProjectStatus.active
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel), nullable=False, default=RiskLevel.low
    )
    assignees: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list of emails
    start_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)

    # Auto-generated project — pending user approval
    is_auto_generated: Mapped[bool] = mapped_column(default=False)
    confirmed: Mapped[bool] = mapped_column(default=False)

    # Relationships
    campaign: Mapped[Optional['Campaign']] = relationship('Campaign', back_populates='projects')
    todos: Mapped[List['Todo']] = relationship('Todo', back_populates='project')
    timeline_events: Mapped[List['TimelineEvent']] = relationship(
        'TimelineEvent', back_populates='project'
    )
    history_events: Mapped[List['HistoryEvent']] = relationship(
        'HistoryEvent', back_populates='project'
    )
    sources: Mapped[List['Source']] = relationship('Source', back_populates='project')
    tickets: Mapped[List['Ticket']] = relationship('Ticket', back_populates='project')


class Ticket(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'tickets'

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='open')
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default='medium')

    project: Mapped['Project'] = relationship('Project', back_populates='tickets')
