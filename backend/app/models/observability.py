from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class AgentRunStatus(str, enum.Enum):
    running = 'running'
    completed = 'completed'
    failed = 'failed'
    cancelled = 'cancelled'


class AgentRun(UUIDPrimaryKey, TimestampMixin, Base):
    """에이전트 실행 로그 — LangSmith 보완용 로컬 로그."""
    __tablename__ = 'agent_runs'

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus), nullable=False, default=AgentRunStatus.running, index=True
    )

    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # LangSmith trace ID (선택)
    langsmith_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped[Optional['Organization']] = relationship('Organization')  # type: ignore[name-defined]
    user: Mapped[Optional['User']] = relationship('User')  # type: ignore[name-defined]


class LLMUsageLog(UUIDPrimaryKey, TimestampMixin, Base):
    """LLM 토큰 사용량 로그."""
    __tablename__ = 'llm_usage_logs'

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True
    )
    agent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True, index=True
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    organization: Mapped[Optional['Organization']] = relationship('Organization')  # type: ignore[name-defined]
    agent_run: Mapped[Optional['AgentRun']] = relationship('AgentRun')  # type: ignore[name-defined]


class ParserRunStatus(str, enum.Enum):
    success = 'success'
    failed = 'failed'
    partial = 'partial'


class ParserRun(UUIDPrimaryKey, TimestampMixin, Base):
    """파서 실행 로그."""
    __tablename__ = 'parser_runs'

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True
    )

    file_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    parser_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[ParserRunStatus] = mapped_column(
        Enum(ParserRunStatus), nullable=False, default=ParserRunStatus.success
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    organization: Mapped[Optional['Organization']] = relationship('Organization')  # type: ignore[name-defined]


class SyncJobStatus(str, enum.Enum):
    running = 'running'
    completed = 'completed'
    failed = 'failed'


class SyncJob(UUIDPrimaryKey, TimestampMixin, Base):
    """연동 동기화 작업 로그 — Celery task 기반."""
    __tablename__ = 'sync_jobs'

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('integrations.id', ondelete='SET NULL'), nullable=True, index=True
    )

    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[SyncJobStatus] = mapped_column(
        Enum(SyncJobStatus), nullable=False, default=SyncJobStatus.running, index=True
    )

    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped[Optional['Organization']] = relationship('Organization')  # type: ignore[name-defined]
    integration: Mapped[Optional['Integration']] = relationship('Integration')  # type: ignore[name-defined]
