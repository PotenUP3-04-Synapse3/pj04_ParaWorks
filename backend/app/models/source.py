from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class SourceType(str, enum.Enum):
    gmail = 'gmail'
    slack = 'slack'
    google_drive = 'google_drive'
    github = 'github'
    calendar = 'calendar'


class PermissionLevel(str, enum.Enum):
    public = 'public'
    team = 'team'
    restricted = 'restricted'


class Source(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'sources'

    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )
    permission_level: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel), nullable=False, default=PermissionLevel.team
    )

    project: Mapped[Optional['Project']] = relationship('Project', back_populates='sources')  # type: ignore[name-defined]
    snippets: Mapped[list['SourceSnippet']] = relationship('SourceSnippet', back_populates='source')


class SourceSnippet(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'source_snippets'

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sources.id', ondelete='CASCADE'), nullable=False, index=True
    )
    snippet_text: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Deduplication hash — MD5 of snippet_text
    version_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # pgvector embedding (text-embedding-3-small = 1536 dims)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)

    # Denormalised columns for fast retriever SQL filtering (no JOIN needed)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    permission_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint('source_id', 'version_hash', name='uq_snippet_source_hash'),
    )

    source: Mapped['Source'] = relationship('Source', back_populates='snippets')
