from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class ServiceType(str, enum.Enum):
    gmail = 'gmail'
    slack = 'slack'
    google_drive = 'google_drive'
    github = 'github'
    calendar = 'calendar'


class IntegrationStatus(str, enum.Enum):
    active = 'active'
    error = 'error'
    disconnected = 'disconnected'
    pending = 'pending'


class Integration(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'integrations'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )

    service_type: Mapped[ServiceType] = mapped_column(Enum(ServiceType), nullable=False)

    # Encrypted OAuth tokens
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Service-specific metadata (channel ids, page tokens, etc.)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob

    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus), nullable=False, default=IntegrationStatus.pending
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped['Organization'] = relationship('Organization', back_populates='integrations')  # type: ignore[name-defined]
