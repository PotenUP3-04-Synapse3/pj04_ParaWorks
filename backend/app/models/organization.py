from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.integration import Integration
    from app.models.permission_policy import PermissionPolicy


class Organization(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'organizations'

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob

    # Relationships
    users: Mapped[List['User']] = relationship('User', back_populates='organization')
    integrations: Mapped[List['Integration']] = relationship(
        'Integration', back_populates='organization'
    )
    permission_policies: Mapped[List['PermissionPolicy']] = relationship(
        'PermissionPolicy', back_populates='organization'
    )
