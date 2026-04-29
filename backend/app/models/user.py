from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.notification import Notification
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    admin = 'admin'
    manager = 'manager'
    member = 'member'
    viewer = 'viewer'


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'users'

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.member
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Google OAuth
    google_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)

    # FK
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization', back_populates='users')
    notifications: Mapped[List['Notification']] = relationship(
        'Notification', back_populates='user'
    )
    audit_logs: Mapped[List['AuditLog']] = relationship('AuditLog', back_populates='user')
