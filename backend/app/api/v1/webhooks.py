"""Webhooks — Slack events, Google Drive push notifications, GitHub webhooks."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_slack_signature, verify_github_signature
from app.models.integration import Integration, ServiceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/webhooks', tags=['webhooks'])


@router.post('/slack/events')
async def slack_events(
    request: Request,
    x_slack_request_timestamp: Optional[str] = Header(None),
    x_slack_signature: Optional[str] = Header(None),
):
    """Receive Slack event callbacks. Must return 200 immediately."""
    body = await request.body()

    if not verify_slack_signature(
        settings.SLACK_SIGNING_SECRET,
        x_slack_request_timestamp or '',
        body,
        x_slack_signature or '',
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Slack signature')

    payload = json.loads(body)

    # URL verification challenge (Slack setup)
    if payload.get('type') == 'url_verification':
        return {'challenge': payload['challenge']}

    # Enqueue processing task — return 200 immediately
    event = payload.get('event', {})
    org_id = _extract_slack_org_id(payload)
    if event and org_id:
        from app.tasks.ingestion_tasks import process_slack_event
        process_slack_event.delay(event, org_id)

    return {'status': 'ok'}


@router.post('/drive/push')
async def drive_push(
    request: Request,
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Receive Google Drive change notifications. Must return 200 immediately."""
    # Verify webhook token
    if x_goog_channel_token != settings.DRIVE_WEBHOOK_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Drive channel token')

    # Find the integration by channel_id in metadata
    if not x_goog_channel_id:
        return {'status': 'ignored'}

    result = await db.execute(
        select(Integration).where(
            Integration.service_type == ServiceType.google_drive,
        )
    )
    integrations = result.scalars().all()

    matching = None
    for intg in integrations:
        meta = intg.metadata_json or {}
        if meta.get('drive_channel_id') == x_goog_channel_id:
            matching = intg
            break

    if not matching:
        logger.warning('Received Drive push for unknown channel %s', x_goog_channel_id)
        return {'status': 'ignored'}

    # Fetch changes and enqueue processing
    from app.tasks.drive_tasks import process_single_drive_file
    from app.connectors.google_drive import list_changes
    from app.core.security import decrypt_token

    access_token = decrypt_token(matching.access_token_encrypted)
    refresh_token = decrypt_token(matching.refresh_token_encrypted)
    page_token = (matching.metadata_json or {}).get('drive_page_token', '1')

    changes, new_page_token = list_changes(access_token, refresh_token, page_token)

    # Update page token
    matching.metadata_json = {**(matching.metadata_json or {}), 'drive_page_token': new_page_token}
    await db.commit()

    from app.tasks.ingestion_tasks import process_drive_changes
    process_drive_changes.delay(
        str(matching.id),
        changes,
        str(matching.organization_id),
    )

    return {'status': 'ok'}


@router.post('/github/events')
async def github_events(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """Receive GitHub webhook events."""
    body = await request.body()

    if not verify_github_signature(settings.GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256 or ''):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid GitHub signature')

    payload = json.loads(body)
    event_type = x_github_event or 'unknown'

    # Only process PR and issue events
    if event_type in ('pull_request', 'issues', 'issue_comment', 'pull_request_review'):
        _enqueue_github_event(event_type, payload)

    return {'status': 'ok'}


def _extract_slack_org_id(payload: Dict[str, Any]) -> Optional[str]:
    """Extract org_id from Slack team_id (stored in Integration metadata)."""
    team_id = payload.get('team_id')
    if not team_id:
        return None
    # In production, look up org_id from team_id via database
    # For now return a sentinel value — the task will look it up
    return team_id


def _enqueue_github_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Enqueue GitHub event processing task."""
    # Normalise to DocumentChunk-compatible format
    event = {}
    if event_type in ('pull_request',):
        event = payload.get('pull_request', {})
        event['type'] = 'pull_request'
    elif event_type in ('issues', 'issue_comment'):
        event = payload.get('issue', {})
        event['type'] = 'issue'

    if event:
        from app.agents.parser_agent import parse_github_event
        from app.tasks.ingestion_tasks import process_slack_event  # reuse same pattern
        # GitHub org_id resolution: use sender login as placeholder
        logger.info('GitHub %s event received, enqueue processing', event_type)
