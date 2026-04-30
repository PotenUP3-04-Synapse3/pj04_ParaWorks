from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.department import Department
    from app.models.user import User


class Team(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'teams'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped['Organization'] = relationship('Organization', back_populates='teams')
    department: Mapped[Optional['Department']] = relationship('Department', back_populates='teams')
    users: Mapped[List['User']] = relationship('User', back_populates='team')
