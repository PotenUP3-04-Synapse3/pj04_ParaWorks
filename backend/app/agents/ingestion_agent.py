"""Ingestion Agent — collects raw data from external APIs for a given integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.agents.base_agent import AgentState, DocumentChunk
from app.core.security import decrypt_token

logger = logging.getLogger(__name__)


async def run_ingestion_agent(
    integration_data: Dict[str, Any],
    since: Optional[datetime] = None,
) -> List[DocumentChunk]:
    """
    Collect raw data from a single integration and return parsed DocumentChunks.
    No LLM calls — pure API polling + parsing.
    """
    service_type = integration_data.get('service_type', '')
    access_token = decrypt_token(integration_data['access_token_encrypted'])
    refresh_token = decrypt_token(integration_data.get('refresh_token_encrypted') or '')
    org_id = str(integration_data.get('organization_id', ''))

    if not since:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

    chunks: List[DocumentChunk] = []

    if service_type == 'gmail':
        chunks = await _ingest_gmail(access_token, refresh_token, since)
    elif service_type == 'slack':
        chunks = await _ingest_slack(access_token, integration_data.get('metadata_json', {}), since)
    elif service_type == 'google_calendar':
        chunks = await _ingest_calendar(access_token, refresh_token, since)
    elif service_type == 'github':
        chunks = await _ingest_github(access_token, integration_data.get('metadata_json', {}), since)

    logger.info('Ingestion agent collected %d chunks from %s', len(chunks), service_type)
    return chunks


async def _ingest_gmail(access_token: str, refresh_token: str, since: datetime) -> List[DocumentChunk]:
    from app.connectors.gmail import list_messages, get_message, is_company_email
    from app.agents.parser_agent import parse_gmail_message
    from app.core.config import settings

    query = f'after:{int(since.timestamp())}'
    message_refs = list_messages(access_token, refresh_token, query=query, max_results=100)
    allowed_domains = settings.allowed_email_domains_list

    chunks = []
    for ref in message_refs:
        msg = get_message(access_token, refresh_token, ref['id'])
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        if not is_company_email(headers.get('From', ''), allowed_domains):
            continue
        chunks.extend(parse_gmail_message(msg))
    return chunks


async def _ingest_slack(bot_token: str, meta: dict, since: datetime) -> List[DocumentChunk]:
    from app.connectors.slack import get_channel_history
    from app.agents.parser_agent import parse_slack_event

    channel_ids = meta.get('channel_ids', [])
    oldest = str(since.timestamp())
    chunks = []
    for channel_id in channel_ids:
        messages = get_channel_history(bot_token, channel=channel_id, oldest=oldest)
        for msg in messages:
            msg['channel'] = channel_id
            chunks.extend(parse_slack_event(msg))
    return chunks


async def _ingest_calendar(access_token: str, refresh_token: str, since: datetime) -> List[DocumentChunk]:
    from app.connectors.calendar import list_events, format_event_text
    from app.agents.parser_agent import parse_drive_document
    from datetime import timedelta, timezone

    events = list_events(
        access_token, refresh_token,
        time_min=since,
        time_max=since + timedelta(days=30),
    )
    chunks = []
    for event in events:
        text = format_event_text(event)
        if text.strip():
            chunks.extend(
                parse_drive_document(
                    text=text,
                    file_id=event.get('id', ''),
                    file_name=event.get('summary', 'event'),
                    mime_type='text/plain',
                    author=event.get('organizer', {}).get('email', ''),
                    modified_time=event.get('start', {}).get('dateTime', ''),
                    permission_level='team',
                )
            )
    return chunks


async def _ingest_github(token: str, meta: dict, since: datetime) -> List[DocumentChunk]:
    from app.connectors.github import get_client
    from app.agents.parser_agent import parse_github_event

    repo_names = meta.get('repositories', [])
    chunks = []
    g = get_client(token)

    for repo_name in repo_names:
        try:
            repo = g.get_repo(repo_name)
            for issue in repo.get_issues(state='all', since=since):
                event = {
                    'id': issue.id,
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body or '',
                    'state': issue.state,
                    'user': {'login': issue.user.login},
                    'html_url': issue.html_url,
                    'created_at': issue.created_at.isoformat(),
                    'type': 'issue',
                }
                chunks.extend(parse_github_event(event))
        except Exception as exc:
            logger.warning('Failed to ingest GitHub repo %s: %s', repo_name, exc)

    return chunks
