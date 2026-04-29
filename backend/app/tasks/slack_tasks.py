"""Slack Celery tasks — 메시지 수집 및 스레드 저장."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    """Celery sync task에서 async 코루틴 실행."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── 팀 ID → Organization ID 해석 ──────────────────────────────────────────────

async def _resolve_organization_id(db, slack_team_id: str) -> Optional[uuid.UUID]:
    """slack_team_id로 SlackWorkspace를 찾아 organization_id를 반환."""
    from sqlalchemy import select
    from app.models.slack import SlackWorkspace

    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.slack_team_id == slack_team_id)
    )
    ws = result.scalar_one_or_none()
    if ws:
        return ws.organization_id

    # 워크스페이스 미등록 — Integration 테이블에서 slack 통합 찾기
    from app.models.integration import Integration, ServiceType
    result = await db.execute(
        select(Integration).where(
            Integration.service_type == ServiceType.slack,
        )
    )
    integrations = result.scalars().all()
    for intg in integrations:
        meta = intg.metadata_json or {}
        if meta.get('team_id') == slack_team_id:
            return intg.organization_id

    return None


# ── ingest_slack_message ──────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_slack_message(self, event_data: Dict[str, Any], team_id: str) -> None:
    """Slack 메시지 이벤트를 DB에 저장한다 (단건).

    Args:
        event_data: Slack Events API의 event 객체
        team_id:    Slack team_id (= payload.team_id)
    """
    async def _do() -> None:
        from app.core.database import get_db_context
        from app.services.slack_service import (
            get_or_create_channel,
            get_or_create_thread,
            get_or_create_workspace,
            increment_thread_message_count,
            save_slack_message,
        )

        channel_slack_id: str = event_data.get('channel', '')
        is_private: bool = event_data.get('channel_type') in ('im', 'mpim', 'private_channel')

        async with get_db_context() as db:
            # 1. Organization 해석
            org_id = await _resolve_organization_id(db, team_id)
            if not org_id:
                logger.warning(
                    'ingest_slack_message: unknown team_id=%s, dropping event', team_id
                )
                return

            # 2. Workspace 조회/생성
            workspace = await get_or_create_workspace(
                db,
                organization_id=org_id,
                slack_team_id=team_id,
            )

            # 3. Channel 조회/생성
            channel = await get_or_create_channel(
                db,
                organization_id=org_id,
                workspace_id=workspace.id,
                slack_channel_id=channel_slack_id,
                is_private=is_private,
            )

            if not channel.is_collection_enabled:
                logger.debug(
                    'ingest_slack_message: collection disabled for channel %s', channel_slack_id
                )
                return

            # 4. 메시지 저장 (unique constraint 기반 dedup)
            msg = await save_slack_message(
                db,
                organization_id=org_id,
                workspace_id=workspace.id,
                channel_id=channel.id,
                slack_channel_db_id=channel.id,
                event=event_data,
            )
            if msg is None:
                return

            # 5. 스레드 조회/생성 (thread_ts가 있는 경우만)
            thread_ts = event_data.get('thread_ts')
            if thread_ts:
                thread = await get_or_create_thread(
                    db,
                    organization_id=org_id,
                    workspace_id=workspace.id,
                    channel_id=channel.id,
                    thread_ts=thread_ts,
                    first_message_at=msg.event_time,
                )
                if thread and thread_ts != msg.slack_message_ts:
                    # 답글이면 스레드 카운터 업데이트
                    await increment_thread_message_count(
                        db, channel.id, thread_ts, msg.event_time
                    )

            await db.commit()
            logger.info(
                'Slack message saved: org=%s channel=%s ts=%s',
                org_id, channel_slack_id, msg.slack_message_ts,
            )

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('ingest_slack_message failed: %s', exc)
        raise self.retry(exc=exc)


# ── fetch_and_save_thread ─────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def fetch_and_save_thread(
    self,
    workspace_db_id: str,
    channel_db_id: str,
    thread_ts: str,
) -> None:
    """Slack API로 스레드 전체를 가져와 DB에 저장한다 (Phase B에서 상세 구현 예정).

    현재는 스레드 메타데이터만 업데이트.
    """
    async def _do() -> None:
        from sqlalchemy import select
        from app.core.database import get_db_context
        from app.models.slack import SlackThread, SlackThreadStatus

        ws_uuid = uuid.UUID(workspace_db_id)
        ch_uuid = uuid.UUID(channel_db_id)

        async with get_db_context() as db:
            result = await db.execute(
                select(SlackThread).where(
                    SlackThread.workspace_id == ws_uuid,
                    SlackThread.channel_id == ch_uuid,
                    SlackThread.thread_ts == thread_ts,
                )
            )
            thread = result.scalar_one_or_none()
            if not thread:
                logger.warning(
                    'fetch_and_save_thread: thread not found ws=%s ch=%s ts=%s',
                    workspace_db_id, channel_db_id, thread_ts,
                )
                return

            # Phase B에서 실제 Slack API 호출로 교체 예정
            # 현재는 상태 플래그만 변경
            if thread.processing_status == SlackThreadStatus.unprocessed:
                thread.processing_status = SlackThreadStatus.processing
                await db.commit()
                logger.info(
                    'Thread queued for processing: %s / %s', channel_db_id, thread_ts
                )

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('fetch_and_save_thread failed: %s', exc)
        raise self.retry(exc=exc)
