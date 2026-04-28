from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class Organization(Base, TimestampMixin):
    __tablename__ = 'organizations'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 콤마 없이 배열로 저장: ["company.com", "subsidiary.co.kr"]
    allowed_domains: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True, default=None)

    departments: Mapped[list[Department]] = relationship(back_populates='organization')
    business_domains: Mapped[list[BusinessDomain]] = relationship(back_populates='organization')


class Department(Base, TimestampMixin):
    __tablename__ = 'departments'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_dept_id: Mapped[str | None] = mapped_column(ForeignKey('departments.id'), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates='departments')
    teams: Mapped[list[Team]] = relationship(back_populates='department')
    children: Mapped[list[Department]] = relationship(back_populates='parent')
    parent: Mapped[Department | None] = relationship(back_populates='children', remote_side='Department.id')


class Team(Base, TimestampMixin):
    __tablename__ = 'teams'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    department_id: Mapped[str] = mapped_column(ForeignKey('departments.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    department: Mapped[Department] = relationship(back_populates='teams')


class BusinessDomain(Base, TimestampMixin):
    __tablename__ = 'business_domains'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates='business_domains')
