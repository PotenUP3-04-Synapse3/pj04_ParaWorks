from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class IntegrationConnection(Base):
    __tablename__ = 'integration_connections'
    __table_args__ = (
        UniqueConstraint('connector_type', 'workspace_id', name='uq_integration_workspace'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connector_type: Mapped[str] = mapped_column(String(32), index=True)
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    workspace_name: Mapped[str] = mapped_column(String(200))
    workspace_url: Mapped[str] = mapped_column(String(500), default='https://slack.com')
    bot_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scopes: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    token_ref: Mapped[str] = mapped_column(String(300))
    masked_bot_token: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default='connected', index=True)
    raw_metadata: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
