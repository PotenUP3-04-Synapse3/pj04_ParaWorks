from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class Integration(Base, TimestampMixin):
    __tablename__ = 'integrations'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    # type: google_drive | gmail | slack | google_calendar
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # status: connected | disconnected | error | syncing
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='disconnected')
    last_synced_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_sync_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
