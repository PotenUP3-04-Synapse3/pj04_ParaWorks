from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class Project(Base, TimestampMixin):
    __tablename__ = 'projects'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='active')  # active|completed|archived
    owner_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    department_id: Mapped[str | None] = mapped_column(ForeignKey('departments.id'), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ended_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column('metadata', JSONB, nullable=True)
