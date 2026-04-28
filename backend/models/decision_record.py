from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.permissions import PermissionLevel
from backend.models.base import TimestampMixin, new_uuid

permission_level_enum = ENUM(
    *[p.value for p in PermissionLevel],
    name='permission_level',
    create_type=True,
)

review_status_enum = ENUM(
    'pending', 'approved', 'rejected', 'archived',
    name='review_status',
    create_type=True,
)


class DecisionRecord(Base, TimestampMixin):
    """의사결정 히스토리 레코드 — 22개 필드 전체 포함."""
    __tablename__ = 'decision_records'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    related_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_department_id: Mapped[str | None] = mapped_column(ForeignKey('departments.id'), nullable=True)
    business_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    decision_summary: Mapped[str] = mapped_column(Text, nullable=False)
    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternatives_considered: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list[str]
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_decision: Mapped[str] = mapped_column(Text, nullable=False)

    decision_maker: Mapped[str | None] = mapped_column(String(320), nullable=True)  # email
    participants: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)   # list[email]
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_links: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    source_snippets: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list[{url, text}]
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    permission_level: Mapped[str] = mapped_column(
        permission_level_enum, nullable=False, default=PermissionLevel.TEAM.value
    )
    review_status: Mapped[str] = mapped_column(
        review_status_enum, nullable=False, default='pending'
    )

    participants_rel: Mapped[list[DecisionParticipant]] = relationship(back_populates='decision')
    evidence_sources: Mapped[list[EvidenceSource]] = relationship(back_populates='decision')


class DecisionParticipant(Base):
    __tablename__ = 'decision_participants'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[str] = mapped_column(ForeignKey('decision_records.id'), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "approver", "contributor" 등

    decision: Mapped[DecisionRecord] = relationship(back_populates='participants_rel')


class EvidenceSource(Base):
    __tablename__ = 'evidence_sources'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[str] = mapped_column(ForeignKey('decision_records.id'), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "gmail"|"slack"|"drive"|"calendar"
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)   # thread_id, file_id 등
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    decision: Mapped[DecisionRecord] = relationship(back_populates='evidence_sources')
