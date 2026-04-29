"""Celery tasks for Google Drive — initial sync and channel renewal."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from sqlalchemy import select

from app.core.database import get_db_context
from app.core.security import decrypt_token
from app.models.integration import Integration, IntegrationStatus, ServiceType
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def initial_drive_sync(self, integration_id: str) -> None:
    """Perform a full initial sync of all Drive files for a new integration."""
    async def _do():
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one_or_none()
            if not integration:
                logger.warning('Integration %s not found', integration_id)
                return

        access_token = decrypt_token(integration.access_token_encrypted)
        refresh_token = decrypt_token(integration.refresh_token_encrypted)

        from app.connectors.google_drive import (
            list_changes, get_start_page_token, get_file_permission_level,
            download_file, register_watch_channel,
        )
        from app.parsers.document_parser import extract_text
        from app.agents.parser_agent import parse_drive_document
        from app.services.ingestion_service import ingest_chunks

        # Register watch channel for future change notifications
        channel_info = register_watch_channel(access_token, refresh_token)
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one_or_none()
            if integration:
                meta = integration.metadata_json or {}
                meta['drive_channel_id'] = channel_info['channel_id']
                meta['drive_resource_id'] = channel_info['resource_id']
                meta['drive_page_token'] = channel_info['page_token']
                meta['drive_channel_expiration'] = channel_info['expiration']
                integration.metadata_json = meta
                await db.commit()

        # Sync changes from the beginning (page_token=1 for full list)
        changes, new_page_token = list_changes(access_token, refresh_token, '1')

        for change in changes:
            if change.get('removed'):
                continue
            file_meta = change.get('file', {})
            if file_meta.get('trashed'):
                continue
            process_single_drive_file.delay(
                integration_id=integration_id,
                file_meta=file_meta,
                org_id=str(integration.organization_id),
            )

        # Save new page token
        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one_or_none()
            if integration:
                meta = integration.metadata_json or {}
                meta['drive_page_token'] = new_page_token
                integration.metadata_json = meta
                await db.commit()

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('initial_drive_sync for %s failed: %s', integration_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_single_drive_file(
    self,
    integration_id: str,
    file_meta: Dict[str, Any],
    org_id: str,
) -> None:
    """Download and ingest a single Drive file."""
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

        from app.connectors.google_drive import get_file_permission_level, download_file
        from app.parsers.document_parser import extract_text
        from app.agents.parser_agent import parse_drive_document
        from app.services.ingestion_service import ingest_chunks

        permission_level = get_file_permission_level(file_meta)
        if permission_level == 'none':
            logger.debug('Skipping file %s — no canRead permission', file_meta.get('id'))
            return

        file_id = file_meta['id']
        mime_type = file_meta.get('mimeType', '')
        file_name = file_meta.get('name', '')

        try:
            content_bytes, actual_mime = download_file(access_token, refresh_token, file_id, mime_type)
        except Exception as exc:
            logger.warning('Failed to download Drive file %s: %s', file_id, exc)
            return

        text = extract_text(content_bytes, actual_mime, file_name)
        if not text.strip():
            return

        author = (file_meta.get('owners') or [{}])[0].get('emailAddress', '')
        modified_time = file_meta.get('modifiedTime', '')
        md5 = file_meta.get('md5Checksum')

        chunks = parse_drive_document(
            text=text,
            file_id=file_id,
            file_name=file_name,
            mime_type=actual_mime,
            author=author,
            modified_time=modified_time,
            md5_checksum=md5,
            permission_level=permission_level,
        )
        if chunks:
            await ingest_chunks(chunks, org_id=org_id)

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('process_single_drive_file %s failed: %s', file_meta.get('id'), exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def renew_all_drive_channels(self) -> None:
    """Renew all expiring Google Drive watch channels (run by Celery Beat daily)."""
    async def _do():
        from datetime import datetime, timezone, timedelta

        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(
                    Integration.service_type == ServiceType.google_drive,
                    Integration.status == IntegrationStatus.active,
                )
            )
            integrations = result.scalars().all()

        for integration in integrations:
            meta = integration.metadata_json or {}
            expiration_str = meta.get('drive_channel_expiration', '')
            if not expiration_str:
                renew_drive_channel.delay(str(integration.id))
                continue

            # Renew if expiring within 2 days
            try:
                exp = datetime.fromtimestamp(int(expiration_str) / 1000, tz=timezone.utc)
                if exp - datetime.now(timezone.utc) < timedelta(days=2):
                    renew_drive_channel.delay(str(integration.id))
            except Exception:
                renew_drive_channel.delay(str(integration.id))

    _run(_do())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def renew_drive_channel(self, integration_id: str) -> None:
    """Stop the old watch channel and register a new one for a single integration."""
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

        from app.connectors.google_drive import stop_watch_channel, register_watch_channel

        meta = integration.metadata_json or {}
        old_channel_id = meta.get('drive_channel_id')
        old_resource_id = meta.get('drive_resource_id')

        if old_channel_id and old_resource_id:
            try:
                stop_watch_channel(access_token, refresh_token, old_channel_id, old_resource_id)
            except Exception as exc:
                logger.warning('Failed to stop old Drive channel: %s', exc)

        channel_info = register_watch_channel(access_token, refresh_token)

        async with get_db_context() as db:
            result = await db.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one_or_none()
            if integration:
                meta = integration.metadata_json or {}
                meta['drive_channel_id'] = channel_info['channel_id']
                meta['drive_resource_id'] = channel_info['resource_id']
                meta['drive_page_token'] = channel_info['page_token']
                meta['drive_channel_expiration'] = channel_info['expiration']
                integration.metadata_json = meta
                await db.commit()

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('renew_drive_channel for %s failed: %s', integration_id, exc)
        raise self.retry(exc=exc)
