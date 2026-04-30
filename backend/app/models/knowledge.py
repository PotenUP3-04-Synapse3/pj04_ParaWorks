from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class DecisionRecord(Base):
    __tablename__ = 'decision_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    decision_summary: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_snippets: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class HistoryEvent(Base):
    __tablename__ = 'history_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    reason: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_snippets: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TimelineEvent(Base):
    __tablename__ = 'timeline_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    result_summary: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_snippets: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Todo(Base):
    __tablename__ = 'todos'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    priority: Mapped[str] = mapped_column(String(32))
    priority_reason: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_snippets: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
