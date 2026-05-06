from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class VectorIndexState(Base):
    __tablename__ = 'vector_index_states'
    __table_args__ = (
        UniqueConstraint('document_id', 'embedding_model', name='uq_vector_index_state_document_model'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[str] = mapped_column(String(200), index=True)
    embedding_model: Mapped[str] = mapped_column(String(120), index=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default='indexed', index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
