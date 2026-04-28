from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class DocumentCollection(Base, TimestampMixin):
    """Google Drive 파일/이메일 첨부/Slack 파일 단위 문서 컬렉션."""
    __tablename__ = 'document_collections'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    # source: "google_drive" | "gmail" | "slack" | "manual"
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)  # file_id, message_id
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    versions: Mapped[list[DocumentVersion]] = relationship(back_populates='collection')
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates='collection')


class DocumentVersion(Base):
    """문서 버전별 diff 추적."""
    __tablename__ = 'document_versions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    collection_id: Mapped[str] = mapped_column(ForeignKey('document_collections.id'), nullable=False, index=True)
    version_label: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "v1", "2025-01-01" 등
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diff_from_previous: Mapped[str | None] = mapped_column(Text, nullable=True)  # unified diff
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column('metadata', JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    collection: Mapped[DocumentCollection] = relationship(back_populates='versions')


class DocumentChunk(Base):
    """RAG 인덱싱용 청크 — pgvector embedding 포함."""
    __tablename__ = 'document_chunks'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    collection_id: Mapped[str] = mapped_column(ForeignKey('document_collections.id'), nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(ForeignKey('document_versions.id'), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # embedding column은 Alembic migration에서 vector(1536)로 직접 추가
    metadata_: Mapped[dict | None] = mapped_column('metadata', JSONB, nullable=True)

    collection: Mapped[DocumentCollection] = relationship(back_populates='chunks')
