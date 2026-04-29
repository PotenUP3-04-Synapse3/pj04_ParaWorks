from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class Document(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'documents'

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sources.id', ondelete='CASCADE'), nullable=False, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, hwp, ...
    storage_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    versions: Mapped[list['DocumentVersion']] = relationship(
        'DocumentVersion', back_populates='document', order_by='DocumentVersion.version_number'
    )


class DocumentVersion(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'document_versions'

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    storage_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    md5_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    document: Mapped['Document'] = relationship('Document', back_populates='versions')
