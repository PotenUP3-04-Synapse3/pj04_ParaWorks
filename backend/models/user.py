from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.permissions import UserRole
from backend.models.base import TimestampMixin, new_uuid

user_role_enum = ENUM(
    *[r.value for r in UserRole],
    name='user_role',
    create_type=True,
)


class User(Base, TimestampMixin):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(user_role_enum, nullable=False, default=UserRole.MEMBER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 소속 부서/팀은 별도 association table 없이 단순화 (추후 확장 가능)
    department_id: Mapped[str | None] = mapped_column(ForeignKey('departments.id'), nullable=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
