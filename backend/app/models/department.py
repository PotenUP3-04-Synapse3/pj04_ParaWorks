from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.team import Team
    from app.models.user import User


class Department(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = 'departments'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Self-referential parent/child (optional hierarchy)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True
    )

    # Relationships
    organization: Mapped['Organization'] = relationship(
        'Organization', back_populates='departments'
    )
    teams: Mapped[List['Team']] = relationship('Team', back_populates='department')
    users: Mapped[List['User']] = relationship('User', back_populates='department')
    children: Mapped[List['Department']] = relationship(
        'Department', back_populates='parent', foreign_keys=[parent_id]
    )
    parent: Mapped[Optional['Department']] = relationship(
        'Department', back_populates='children', remote_side='Department.id', foreign_keys=[parent_id]
    )
