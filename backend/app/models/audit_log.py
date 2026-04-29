from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class AuditLog(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'audit_logs'

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(20), nullable=False)   # GET, POST, PATCH, DELETE
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resource_path: Mapped[str] = mapped_column(String(512), nullable=False)

    ip_addr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped[Optional['User']] = relationship('User', back_populates='audit_logs')  # type: ignore[name-defined]
