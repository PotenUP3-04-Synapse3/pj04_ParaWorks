from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class ReviewItem(Base):
    __tablename__ = 'review_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))
    source_links: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_snippets: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default='pending_review', index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
