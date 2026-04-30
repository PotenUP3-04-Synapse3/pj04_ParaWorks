from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class HandoverPacket(UUIDPrimaryKey, TimestampMixin, Base):
    """인수인계 패킷 — 담당자 변경 시 생성되는 구조화된 인수인계 문서."""
    __tablename__ = 'handover_packets'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    from_user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    to_user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 요약 섹션
    background_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pending_decisions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    key_contacts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [{name, email, role}]
    important_links: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 참조 자산 IDs
    linked_asset_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    linked_decision_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    effective_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization')  # type: ignore[name-defined]
    project: Mapped[Optional['Project']] = relationship('Project')  # type: ignore[name-defined]
