"""Parser Agent — converts raw source data to standardized DocumentChunks."""
from __future__ import annotations

import logging
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.agents.base_agent import DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.RAG_CHUNK_SIZE,
    chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    length_function=len,
)


def parse_slack_event(event: dict) -> List[DocumentChunk]:
    text = event.get('text', '')
    if not text.strip():
        return []

    chunks = _splitter.split_text(text)
    return [
        DocumentChunk(
            source_type='slack',
            source_id=event.get('ts', ''),
            source_url=_build_slack_url(event),
            project_id=None,
            campaign_id=None,
            author=event.get('user', ''),
            participants=_extract_slack_participants(event),
            timestamp=_ts_to_iso(event.get('ts', '0')),
            channel=event.get('channel'),
            thread_id=event.get('thread_ts'),
            document_version=None,
            permission_level='team',
            tags=_extract_slack_tags(event),
            chunk_index=i,
            total_chunks=len(chunks),
            text=chunk,
        )
        for i, chunk in enumerate(chunks)
    ]


def parse_gmail_message(message: dict) -> List[DocumentChunk]:
    body = _extract_gmail_body(message)
    if not body.strip():
        return []

    chunks = _splitter.split_text(body)
    headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
    return [
        DocumentChunk(
            source_type='gmail',
            source_id=message.get('id', ''),
            source_url=f'https://mail.google.com/mail/u/0/#inbox/{message.get("id", "")}',
            project_id=None,
            campaign_id=None,
            author=headers.get('From', ''),
            participants=_extract_email_participants(headers),
            timestamp=_gmail_date_to_iso(headers.get('Date', '')),
            channel=None,
            thread_id=message.get('threadId'),
            document_version=None,
            permission_level='restricted',
            tags=[],
            chunk_index=i,
            total_chunks=len(chunks),
            text=chunk,
        )
        for i, chunk in enumerate(chunks)
    ]


def parse_drive_document(
    text: str,
    file_id: str,
    file_name: str,
    mime_type: str,
    author: str,
    modified_time: str,
    md5_checksum: Optional[str] = None,
    permission_level: str = 'team',
) -> List[DocumentChunk]:
    if not text.strip():
        return []

    chunks = _splitter.split_text(text)
    source_url = f'https://drive.google.com/file/d/{file_id}'
    return [
        DocumentChunk(
            source_type='google_drive',
            source_id=file_id,
            source_url=source_url,
            project_id=None,
            campaign_id=None,
            author=author,
            participants=[author],
            timestamp=modified_time,
            channel=None,
            thread_id=None,
            document_version=md5_checksum,
            permission_level=permission_level,
            tags=[mime_type],
            chunk_index=i,
            total_chunks=len(chunks),
            text=chunk,
        )
        for i, chunk in enumerate(chunks)
    ]


def parse_github_event(event: dict) -> List[DocumentChunk]:
    event_type = event.get('type', 'unknown')
    body = _extract_github_body(event)
    if not body.strip():
        return []

    chunks = _splitter.split_text(body)
    return [
        DocumentChunk(
            source_type='github',
            source_id=str(event.get('id', '')),
            source_url=event.get('html_url', ''),
            project_id=None,
            campaign_id=None,
            author=event.get('user', {}).get('login', ''),
            participants=_extract_github_participants(event),
            timestamp=event.get('created_at', ''),
            channel=None,
            thread_id=str(event.get('number', '')),
            document_version=None,
            permission_level='team',
            tags=[event_type],
            chunk_index=i,
            total_chunks=len(chunks),
            text=chunk,
        )
        for i, chunk in enumerate(chunks)
    ]


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_slack_url(event: dict) -> str:
    channel = event.get('channel', '')
    ts = event.get('ts', '').replace('.', '')
    return f'https://app.slack.com/client/{channel}/{ts}'


def _extract_slack_participants(event: dict) -> List[str]:
    participants = [event.get('user', '')]
    mentions = [
        m[2:-1] for m in event.get('text', '').split()
        if m.startswith('<@') and m.endswith('>')
    ]
    return list(set(participants + mentions))


def _extract_slack_tags(event: dict) -> List[str]:
    text = event.get('text', '')
    return [w[1:] for w in text.split() if w.startswith('#')]


def _ts_to_iso(ts: str) -> str:
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return ts


def _extract_gmail_body(message: dict) -> str:
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    if parts:
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                import base64
                data = part.get('body', {}).get('data', '')
                try:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                except Exception:
                    pass
    body_data = payload.get('body', {}).get('data', '')
    if body_data:
        import base64
        try:
            return base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
        except Exception:
            pass
    return ''


def _extract_email_participants(headers: dict) -> List[str]:
    participants = []
    for field in ('From', 'To', 'Cc'):
        val = headers.get(field, '')
        if val:
            participants.extend(addr.strip() for addr in val.split(','))
    return participants


def _gmail_date_to_iso(date_str: str) -> str:
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str).isoformat()
    except Exception:
        return date_str


def _extract_github_body(event: dict) -> str:
    parts = []
    title = event.get('title', '')
    body = event.get('body', '') or ''
    if title:
        parts.append(f'Title: {title}')
    if body:
        parts.append(body)
    # PR review comments
    for comment in event.get('comments', []):
        parts.append(comment.get('body', ''))
    return '\n\n'.join(parts)


def _extract_github_participants(event: dict) -> List[str]:
    participants = []
    if user := event.get('user', {}).get('login'):
        participants.append(user)
    for r in event.get('requested_reviewers', []):
        if login := r.get('login'):
            participants.append(login)
    return list(set(participants))
