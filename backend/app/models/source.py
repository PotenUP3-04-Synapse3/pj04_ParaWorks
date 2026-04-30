from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Source(Base):
    __tablename__ = 'sources'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source_url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    raw_metadata: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    documents: Mapped[list['Document']] = relationship(back_populates='source')


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    title: Mapped[str] = mapped_column(String(300))
    current_version: Mapped[str] = mapped_column(String(64), default='v1')
    source: Mapped[Source] = relationship(back_populates='documents')
    versions: Mapped[list['DocumentVersion']] = relationship(back_populates='document')


class DocumentVersion(Base):
    __tablename__ = 'document_versions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id'), index=True)
    version: Mapped[str] = mapped_column(String(64), default='v1')
    body: Mapped[str] = mapped_column(Text)
    document: Mapped[Document] = relationship(back_populates='versions')
    chunks: Mapped[list['DocumentChunk']] = relationship(back_populates='version')


class DocumentChunk(Base):
    __tablename__ = 'document_chunks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey('document_versions.id'), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    source_snippet: Mapped[str] = mapped_column(Text)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    metadata_: Mapped[dict] = mapped_column('metadata', MutableDict.as_mutable(JSON), default=dict)
    version: Mapped[DocumentVersion] = relationship(back_populates='chunks')
