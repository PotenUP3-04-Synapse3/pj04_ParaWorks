"""Decision Record model — AI가 추출한 의사결정 내역."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class DecisionRecordStatus(str, enum.Enum):
    draft = 'draft'
    approved = 'approved'
    rejected = 'rejected'


class DecisionRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """의사결정 기록 — 반드시 source evidence를 포함해야 approved 가능."""
    __tablename__ = 'decision_records'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    # project mapping은 선택 (Slack unmapped thread에서도 생성 가능)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)

    situation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ["대안 A: ...", "대안 B: ..."]
    alternatives_considered: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    decision_maker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    participants: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )

    # Source evidence — 없으면 approved로 변경 불가
    source_links: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    source_snippets: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    missing_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[DecisionRecordStatus] = mapped_column(
        Enum(DecisionRecordStatus, create_type=False), nullable=False,
        default=DecisionRecordStatus.draft,
    )

    # 어느 Slack thread에서 생성됐는지 추적
    source_slack_thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('slack_threads.id', ondelete='SET NULL'), nullable=True,
    )

    # relationships
    project: Mapped[Optional['Project']] = relationship(  # type: ignore[name-defined]
        'Project', foreign_keys=[project_id],
    )
