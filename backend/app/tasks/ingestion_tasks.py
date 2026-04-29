"""Celery tasks for document ingestion (Slack, Gmail, Calendar)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from celery import shared_task
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db_context
from app.core.security import decrypt_token
from app.models.integration import Integration, IntegrationStatus, ServiceType
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_slack_event(self, event_data: Dict[str, Any], org_id: str) -> None:
    """Parse a single Slack webhook event and ingest into the pipeline."""
    try:
        from app.agents.parser_agent import parse_slack_event
        from app.services.ingestion_service import ingest_chunks

        chunks = parse_slack_event(event_data)
        if not chunks:
            return

        _run(ingest_chunks(chunks, org_id=org_id))
    except Exception as exc:
        logger.exception('process_slack_event failed: %s', exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_drive_changes(
    self,
    integration_id: str,
    changes: List[Dict[str, Any]],
    org_id: str,
) -> None:
    """Process Drive file changes from a webhook notification."""
    try:
        from app.tasks.drive_tasks import process_single_drive_file

        for change in changes:
            if change.get('removed'):
                continue
            file_meta = change.get('file', {})
            if file_meta.get('trashed'):
                continue
            process_single_drive_file.delay(
                integration_id=integration_id,
                file_meta=file_meta,
                org_id=org_id,
            )
    except Exception as exc:
        logger.exception('process_drive_changes failed: %s', exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_all_gmail(self) -> None:
    """Sync Gmail for all active integrations (triggered by Celery Beat)."""
    async def _do():
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(
                    Integration.service_type == ServiceType.gmail,
                    Integration.status == IntegrationStatus.active,
                )
            )
            integrations = result.scalars().all()

        for integration in integrations:
            sync_gmail_for_integration.delay(str(integration.id))

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('sync_all_gmail failed: %s', exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_gmail_for_integration(self, integration_id: str) -> None:
    """Sync Gmail messages for a single integration."""
    async def _do():
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one_or_none()
            if not integration:
                return

        access_token = decrypt_token(integration.access_token_encrypted)
        refresh_token = decrypt_token(integration.refresh_token_encrypted)

        from app.connectors.gmail import is_company_email, list_messages, get_message
        from app.agents.parser_agent import parse_gmail_message
        from app.services.ingestion_service import ingest_chunks

        message_ids = list_messages(access_token, refresh_token, query='newer_than:1d', max_results=100)

        allowed_domains = settings.allowed_email_domains_list

        for msg_ref in message_ids:
            msg = get_message(access_token, refresh_token, msg_ref['id'])
            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            from_email = headers.get('From', '')

            # Domain filter — only ingest company emails
            if not is_company_email(from_email, allowed_domains):
                continue

            chunks = parse_gmail_message(msg)
            if chunks:
                await ingest_chunks(chunks, org_id=str(integration.organization_id))

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('sync_gmail_for_integration %s failed: %s', integration_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_all_calendar(self) -> None:
    """Sync Google Calendar for all active integrations."""
    async def _do():
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(
                    Integration.service_type == ServiceType.google_calendar,
                    Integration.status == IntegrationStatus.active,
                )
            )
            integrations = result.scalars().all()

        for integration in integrations:
            sync_calendar_for_integration.delay(str(integration.id))

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('sync_all_calendar failed: %s', exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_calendar_for_integration(self, integration_id: str) -> None:
    """Sync Calendar events for a single integration."""
    async def _do():
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one_or_none()
            if not integration:
                return

        access_token = decrypt_token(integration.access_token_encrypted)
        refresh_token = decrypt_token(integration.refresh_token_encrypted)

        from app.connectors.calendar import list_events, format_event_text
        from app.agents.parser_agent import parse_drive_document
        from app.services.ingestion_service import ingest_chunks
        from datetime import datetime, timedelta, timezone

        events = list_events(
            access_token,
            refresh_token,
            time_min=datetime.now(timezone.utc),
            time_max=datetime.now(timezone.utc) + timedelta(days=30),
        )

        for event in events:
            text = format_event_text(event)
            if not text.strip():
                continue

            chunks = parse_drive_document(
                text=text,
                file_id=event.get('id', ''),
                file_name=event.get('summary', 'calendar_event'),
                mime_type='text/plain',
                author=event.get('organizer', {}).get('email', ''),
                modified_time=event.get('start', {}).get('dateTime', ''),
                permission_level='team',
            )
            if chunks:
                await ingest_chunks(chunks, org_id=str(integration.organization_id))

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('sync_calendar_for_integration %s failed: %s', integration_id, exc)
        raise self.retry(exc=exc)
