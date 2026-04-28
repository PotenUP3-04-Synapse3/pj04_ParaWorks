from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.core.permissions import PermissionLevel
from backend.models.base import TimestampMixin, new_uuid
from backend.models.decision_record import permission_level_enum

asset_type_enum = ENUM(
    'document', 'decision', 'process', 'pattern', 'template', 'faq', 'other',
    name='asset_type',
    create_type=True,
)


class KnowledgeAsset(Base, TimestampMixin):
    """암묵지 자산화 엔티티 — 16개 필드 전체 포함."""
    __tablename__ = 'knowledge_assets'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(asset_type_enum, nullable=False, default='document')

    related_projects: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    related_departments: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    related_decisions: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)

    source_links: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    tags: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)

    permission_level: Mapped[str] = mapped_column(
        permission_level_enum, nullable=False, default=PermissionLevel.TEAM.value
    )
    freshness_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    # 외부 고객사 데이터 격리 플래그
    is_external_client: Mapped[bool] = mapped_column(default=False, nullable=False)
    external_data_policy: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 정책 미정
