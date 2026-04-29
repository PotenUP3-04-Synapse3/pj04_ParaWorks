"""Slack integration models — workspace, channel, message, thread."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKey


# ── Enums ─────────────────────────────────────────────────────────────────────

class SlackChannelPermission(str, enum.Enum):
    public = 'public'
    team = 'team'
    restricted = 'restricted'


class SlackMessageType(str, enum.Enum):
    message = 'message'        # 일반 채널 메시지
    reply = 'reply'            # 스레드 답글
    bot_message = 'bot_message'  # 봇 메시지


class SlackIngestionStatus(str, enum.Enum):
    pending = 'pending'        # 저장됨, 아직 처리 안 됨
    processing = 'processing'  # 처리 중
    done = 'done'              # 완료
    failed = 'failed'          # 실패


class SlackThreadStatus(str, enum.Enum):
    unprocessed = 'unprocessed'  # 수집됨, AI 분석 전
    processing = 'processing'    # AI 분석 중
    done = 'done'                # AI 분석 완료
    failed = 'failed'            # 분석 실패
    needs_review = 'needs_review'  # 검토 필요


# ── SlackWorkspace ────────────────────────────────────────────────────────────

class SlackWorkspace(UUIDPrimaryKey, TimestampMixin, Base):
    """Slack 워크스페이스 — 조직에 설치된 Slack app 단위."""
    __tablename__ = 'slack_workspaces'

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    slack_team_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bot_user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # xoxb- 봇 토큰 — 암호화 저장
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    installed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
    )
    installed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # relationships
    channels: Mapped[list['SlackChannel']] = relationship(
        'SlackChannel', back_populates='workspace', cascade='all, delete-orphan',
    )
    messages: Mapped[list['SlackMessage']] = relationship(
        'SlackMessage', back_populates='workspace',
    )
    threads: Mapped[list['SlackThread']] = relationship(
        'SlackThread', back_populates='workspace',
    )


# ── SlackChannel ──────────────────────────────────────────────────────────────

class SlackChannel(UUIDPrimaryKey, TimestampMixin, Base):
    """Slack 채널 — 수집 정책과 권한 수준을 포함."""
    __tablename__ = 'slack_channels'
    __table_args__ = (
        UniqueConstraint('workspace_id', 'slack_channel_id', name='uq_slack_channel'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('slack_workspaces.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    slack_channel_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 관리자가 수집을 활성화한 채널만 처리
    is_collection_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    # private channel은 관리자 승인 후 restricted → team 승격
    permission_level: Mapped[SlackChannelPermission] = mapped_column(
        Enum(SlackChannelPermission, create_type=False), nullable=False,
        default=SlackChannelPermission.team,
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # relationships
    workspace: Mapped['SlackWorkspace'] = relationship(
        'SlackWorkspace', back_populates='channels',
    )
    messages: Mapped[list['SlackMessage']] = relationship(
        'SlackMessage', back_populates='channel',
    )
    threads: Mapped[list['SlackThread']] = relationship(
        'SlackThread', back_populates='channel',
    )


# ── SlackMessage ──────────────────────────────────────────────────────────────

class SlackMessage(UUIDPrimaryKey, TimestampMixin, Base):
    """Slack 메시지 원본 — 채널 메시지, 스레드 답글 포함."""
    __tablename__ = 'slack_messages'
    __table_args__ = (
        # Slack 메시지 중복 방지: (channel, ts) 조합이 고유 식별자
        UniqueConstraint(
            'channel_id', 'slack_message_ts',
            name='uq_slack_message_ts',
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('slack_workspaces.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('slack_channels.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )

    # Slack 원본 타임스탬프 (= Slack의 고유 메시지 ID)
    slack_message_ts: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # 스레드 루트 타임스탬프. 루트 메시지면 slack_message_ts와 동일
    thread_ts: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    # 답글인 경우 부모 메시지 (DB UUID)
    parent_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('slack_messages.id', ondelete='SET NULL'), nullable=True,
    )

    # 작성자 정보
    author_slack_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author_display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 본문
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    message_type: Mapped[SlackMessageType] = mapped_column(
        Enum(SlackMessageType, create_type=False), nullable=False, default=SlackMessageType.message,
    )

    # Slack permalink
    permalink: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # 첨부파일
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attachments_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # 리액션 목록
    reactions_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # 멘션된 사용자 ID 목록
    mentioned_user_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # 수정/삭제 이력
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 이벤트 발생 시각 (float ts → datetime 변환)
    event_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )

    ingestion_status: Mapped[SlackIngestionStatus] = mapped_column(
        Enum(SlackIngestionStatus, create_type=False), nullable=False,
        default=SlackIngestionStatus.pending,
    )

    # Source 레코드와 연결 (분석 후 생성)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('sources.id', ondelete='SET NULL'), nullable=True,
    )

    # relationships
    workspace: Mapped['SlackWorkspace'] = relationship(
        'SlackWorkspace', back_populates='messages',
    )
    channel: Mapped['SlackChannel'] = relationship(
        'SlackChannel', back_populates='messages',
    )
    replies: Mapped[list['SlackMessage']] = relationship(
        'SlackMessage',
        foreign_keys=[parent_message_id],
        back_populates='parent_message',
    )
    parent_message: Mapped[Optional['SlackMessage']] = relationship(
        'SlackMessage',
        foreign_keys=[parent_message_id],
        back_populates='replies',
        remote_side='SlackMessage.id',
    )


# ── SlackThread ───────────────────────────────────────────────────────────────

class SlackThread(UUIDPrimaryKey, TimestampMixin, Base):
    """Slack 스레드 — thread_ts 기준으로 묶인 대화 단위."""
    __tablename__ = 'slack_threads'
    __table_args__ = (
        UniqueConstraint('channel_id', 'thread_ts', name='uq_slack_thread_ts'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('slack_workspaces.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('slack_channels.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )

    # Slack 스레드 식별자 (루트 메시지 ts)
    thread_ts: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # AI가 생성하는 필드 (Phase C에서 채워짐)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    participant_user_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    permalink: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Project/Domain 매핑 (Phase C에서 채워짐)
    mapped_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('projects.id', ondelete='SET NULL'), nullable=True,
    )
    mapped_department_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mapped_business_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    processing_status: Mapped[SlackThreadStatus] = mapped_column(
        Enum(SlackThreadStatus, create_type=False), nullable=False,
        default=SlackThreadStatus.unprocessed,
    )

    # relationships
    workspace: Mapped['SlackWorkspace'] = relationship(
        'SlackWorkspace', back_populates='threads',
    )
    channel: Mapped['SlackChannel'] = relationship(
        'SlackChannel', back_populates='threads',
    )
