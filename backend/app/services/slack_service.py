"""Slack service — DB 저장/조회 헬퍼 (API 호출 없는 순수 DB 레이어)."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack import (
    SlackChannel,
    SlackChannelPermission,
    SlackIngestionStatus,
    SlackMessage,
    SlackMessageType,
    SlackThread,
    SlackThreadStatus,
    SlackWorkspace,
)

logger = logging.getLogger(__name__)


# ── Workspace ─────────────────────────────────────────────────────────────────

async def get_workspace_by_team_id(
    db: AsyncSession, slack_team_id: str
) -> Optional[SlackWorkspace]:
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.slack_team_id == slack_team_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_workspace(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    slack_team_id: str,
    name: str = 'Unknown Workspace',
    bot_user_id: Optional[str] = None,
    access_token_encrypted: Optional[str] = None,
) -> SlackWorkspace:
    ws = await get_workspace_by_team_id(db, slack_team_id)
    if ws:
        return ws

    ws = SlackWorkspace(
        organization_id=organization_id,
        slack_team_id=slack_team_id,
        name=name,
        bot_user_id=bot_user_id,
        access_token_encrypted=access_token_encrypted,
        is_active=True,
    )
    db.add(ws)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        ws = await get_workspace_by_team_id(db, slack_team_id)
    return ws


# ── Channel ───────────────────────────────────────────────────────────────────

async def get_channel_by_slack_id(
    db: AsyncSession, workspace_id: uuid.UUID, slack_channel_id: str
) -> Optional[SlackChannel]:
    result = await db.execute(
        select(SlackChannel).where(
            SlackChannel.workspace_id == workspace_id,
            SlackChannel.slack_channel_id == slack_channel_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_channel(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    slack_channel_id: str,
    name: str = 'unknown',
    is_private: bool = False,
) -> SlackChannel:
    ch = await get_channel_by_slack_id(db, workspace_id, slack_channel_id)
    if ch:
        return ch

    permission = (
        SlackChannelPermission.restricted if is_private else SlackChannelPermission.team
    )
    ch = SlackChannel(
        organization_id=organization_id,
        workspace_id=workspace_id,
        slack_channel_id=slack_channel_id,
        name=name,
        is_private=is_private,
        is_collection_enabled=True,
        permission_level=permission,
    )
    db.add(ch)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        ch = await get_channel_by_slack_id(db, workspace_id, slack_channel_id)
    return ch


# ── Message ───────────────────────────────────────────────────────────────────

async def get_message_by_ts(
    db: AsyncSession, channel_id: uuid.UUID, slack_message_ts: str
) -> Optional[SlackMessage]:
    result = await db.execute(
        select(SlackMessage).where(
            SlackMessage.channel_id == channel_id,
            SlackMessage.slack_message_ts == slack_message_ts,
        )
    )
    return result.scalar_one_or_none()


def _ts_to_datetime(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, TypeError):
        return None


def _extract_mentioned_users(text: str) -> list[str]:
    """<@U12345> 형태 멘션 추출."""
    return re.findall(r'<@([A-Z0-9]+)>', text or '')


async def save_slack_message(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    channel_id: uuid.UUID,
    slack_channel_db_id: uuid.UUID,
    event: dict,
    parent_message_id: Optional[uuid.UUID] = None,
) -> Optional[SlackMessage]:
    """Slack 이벤트로부터 메시지를 저장한다 (중복 시 기존 반환)."""
    ts = event.get('ts') or event.get('event_ts')
    if not ts:
        logger.warning('Slack event has no ts: %s', event)
        return None

    text = event.get('text', '')
    author = event.get('user') or event.get('bot_id') or 'unknown'
    thread_ts = event.get('thread_ts')

    # 메시지 유형 결정
    if event.get('bot_id'):
        msg_type = SlackMessageType.bot_message
    elif thread_ts and thread_ts != ts:
        msg_type = SlackMessageType.reply
    else:
        msg_type = SlackMessageType.message

    # 기존 메시지 중복 체크
    existing = await get_message_by_ts(db, slack_channel_db_id, ts)
    if existing:
        return existing

    msg = SlackMessage(
        organization_id=organization_id,
        workspace_id=workspace_id,
        channel_id=slack_channel_db_id,
        slack_message_ts=ts,
        thread_ts=thread_ts,
        parent_message_id=parent_message_id,
        author_slack_user_id=author,
        text=text,
        message_type=msg_type,
        has_attachments=bool(event.get('attachments') or event.get('files')),
        attachments_json=event.get('attachments'),
        mentioned_user_ids=_extract_mentioned_users(text) or None,
        event_time=_ts_to_datetime(ts),
        ingestion_status=SlackIngestionStatus.pending,
    )
    db.add(msg)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        msg = await get_message_by_ts(db, slack_channel_db_id, ts)
    return msg


# ── Thread ────────────────────────────────────────────────────────────────────

async def get_thread_by_ts(
    db: AsyncSession, channel_id: uuid.UUID, thread_ts: str
) -> Optional[SlackThread]:
    result = await db.execute(
        select(SlackThread).where(
            SlackThread.channel_id == channel_id,
            SlackThread.thread_ts == thread_ts,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_thread(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    workspace_id: uuid.UUID,
    channel_id: uuid.UUID,
    thread_ts: str,
    first_message_at: Optional[datetime] = None,
) -> SlackThread:
    thread = await get_thread_by_ts(db, channel_id, thread_ts)
    if thread:
        return thread

    thread = SlackThread(
        organization_id=organization_id,
        workspace_id=workspace_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
        first_message_at=first_message_at,
        last_message_at=first_message_at,
        message_count=1,
        processing_status=SlackThreadStatus.unprocessed,
    )
    db.add(thread)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        thread = await get_thread_by_ts(db, channel_id, thread_ts)
    return thread


async def increment_thread_message_count(
    db: AsyncSession, channel_id: uuid.UUID, thread_ts: str, event_time: Optional[datetime]
) -> None:
    """스레드 메시지 수 증가 + last_message_at 업데이트."""
    thread = await get_thread_by_ts(db, channel_id, thread_ts)
    if thread:
        thread.message_count += 1
        if event_time:
            thread.last_message_at = event_time
