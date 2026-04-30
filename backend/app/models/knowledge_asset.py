from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class KnowledgeAssetType(str, enum.Enum):
    decision = 'decision'
    guideline = 'guideline'
    retrospective = 'retrospective'
    runbook = 'runbook'
    template = 'template'
    reference = 'reference'


class KnowledgeAsset(UUIDPrimaryKey, TimestampMixin, Base):
    """큐레이션된 지식 자산 — 결정, 가이드라인, 회고 등의 공식 문서."""
    __tablename__ = 'knowledge_assets'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    related_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )
    related_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('decision_records.id', ondelete='SET NULL'), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    asset_type: Mapped[KnowledgeAssetType] = mapped_column(
        Enum(KnowledgeAssetType), nullable=False, index=True
    )
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    business_domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # 담당자
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization')  # type: ignore[name-defined]
    related_project: Mapped[Optional['Project']] = relationship('Project')  # type: ignore[name-defined]
