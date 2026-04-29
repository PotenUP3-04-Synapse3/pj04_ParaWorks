from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


class AccessLevel(str, enum.Enum):
    none = 'none'
    read = 'read'
    full = 'full'


class PermissionPolicy(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'permission_policies'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)           # admin, manager, member, viewer
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)  # history, todo, timeline, ...
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel), nullable=False, default=AccessLevel.read
    )

    organization: Mapped['Organization'] = relationship('Organization', back_populates='permission_policies')  # type: ignore[name-defined]
