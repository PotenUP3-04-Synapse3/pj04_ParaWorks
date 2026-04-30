from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class SimilarCase(UUIDPrimaryKey, TimestampMixin, Base):
    """유사 사례 매핑 — 새 히스토리/결정이 과거 유사 사례와 연결될 때 생성."""
    __tablename__ = 'similar_cases'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # 소스: HistoryEvent 또는 DecisionRecord 중 하나
    source_history_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('history_events.id', ondelete='CASCADE'), nullable=True, index=True
    )
    source_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('decision_records.id', ondelete='CASCADE'), nullable=True, index=True
    )

    # 매핑 대상: 같은 타입으로 연결
    target_history_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('history_events.id', ondelete='CASCADE'), nullable=True, index=True
    )
    target_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('decision_records.id', ondelete='CASCADE'), nullable=True, index=True
    )

    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization')  # type: ignore[name-defined]


class RepeatedMistakePattern(UUIDPrimaryKey, TimestampMixin, Base):
    """반복 실수 패턴 — 유사한 실수가 반복될 때 감지 및 경고용."""
    __tablename__ = 'repeated_mistake_patterns'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )

    pattern_title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurrence_count: Mapped[int] = mapped_column(default=1, nullable=False)
    related_case_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    business_domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization')  # type: ignore[name-defined]
