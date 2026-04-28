from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class SourcePermission(Base, TimestampMixin):
    """원본 소스(Drive/Slack) 권한 캐시 — 주기적 동기화."""
    __tablename__ = 'source_permissions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    permission_role: Mapped[str] = mapped_column(String(50), nullable=False)  # "owner"|"writer"|"reader"


class HandoverPacket(Base, TimestampMixin):
    """인수인계 자동화 패킷."""
    __tablename__ = 'handover_packets'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    from_user_email: Mapped[str] = mapped_column(String(320), nullable=False)
    to_user_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_projects: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    decision_record_ids: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    knowledge_asset_ids: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    key_contacts: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    open_issues: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='draft')


class SimilarCase(Base, TimestampMixin):
    """유사 사례 인덱스 — 반복 실수 방지."""
    __tablename__ = 'similar_cases'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    source_record_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "decision"|"pattern"
    source_record_id: Mapped[str] = mapped_column(String(36), nullable=False)
    similar_record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    similar_record_id: Mapped[str] = mapped_column(String(36), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    similarity_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RetrospectiveInsight(Base, TimestampMixin):
    __tablename__ = 'retrospective_insights'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    insight: Mapped[str] = mapped_column(Text, nullable=False)
    related_decision_ids: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    tags: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)


class RiskPattern(Base, TimestampMixin):
    __tablename__ = 'risk_patterns'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(default=1, nullable=False)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)


class RepeatedMistakePattern(Base, TimestampMixin):
    __tablename__ = 'repeated_mistake_patterns'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(default=1, nullable=False)
    last_occurred_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prevention_note: Mapped[str | None] = mapped_column(Text, nullable=True)
