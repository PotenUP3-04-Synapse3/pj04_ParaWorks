from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class DecisionReviewStatus(str, enum.Enum):
    draft = 'draft'
    pending_review = 'pending_review'
    approved = 'approved'
    rejected = 'rejected'
    needs_more_evidence = 'needs_more_evidence'
    archived = 'archived'


class DecisionPermissionLevel(str, enum.Enum):
    public = 'public'       # 전사 공개
    team = 'team'           # 팀/부서 공개
    restricted = 'restricted'  # 관련자만


class DecisionRecord(UUIDPrimaryKey, TimestampMixin, Base):
    """공식 의사결정 자산 — 회사 전체 범위의 결정 이력."""
    __tablename__ = 'decision_records'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    related_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    decision_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    situation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives_considered: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_maker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    participants: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [email, ...]

    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    permission_level: Mapped[DecisionPermissionLevel] = mapped_column(
        Enum(DecisionPermissionLevel),
        nullable=False,
        default=DecisionPermissionLevel.team,
    )
    review_status: Mapped[DecisionReviewStatus] = mapped_column(
        Enum(DecisionReviewStatus),
        nullable=False,
        default=DecisionReviewStatus.draft,
    )

    source_links: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    source_snippets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # business_domain 태그 (e.g. "product", "engineering", "marketing")
    business_domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization')  # type: ignore[name-defined]
    related_project: Mapped[Optional['Project']] = relationship('Project')  # type: ignore[name-defined]
