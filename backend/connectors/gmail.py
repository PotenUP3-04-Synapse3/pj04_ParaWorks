from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from email import message_from_bytes
from typing import Any

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.connectors.base import BaseConnector, RawDocument
from backend.core.config import settings

log = structlog.get_logger(__name__)

# PII/민감정보 마스킹 패턴
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b\d{3}-\d{4}-\d{4}\b'), '[PHONE]'),              # 한국 휴대전화
    (re.compile(r'\b\d{6}-[1-4]\d{6}\b'), '[RESIDENT_NO]'),         # 주민등록번호
    (re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b'), '[CARD_NO]'),       # 카드번호
    (re.compile(r'\b\d{10,16}\b'), '[ACCOUNT_NO]'),                  # 계좌번호 유사
]


def _mask_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _build_credentials():
    sa_json = settings.google_service_account_json
    if os.path.exists(sa_json):
        creds = service_account.Credentials.from_service_account_file(
            sa_json,
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.metadata',
            ],
        )
    else:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.metadata',
            ],
        )
    return creds.with_subject(settings.google_subject_email)


class GmailConnector(BaseConnector):
    def __init__(self):
        self._service = None

    async def authenticate(self) -> None:
        creds = _build_credentials()
        self._service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        log.info('gmail.authenticated')

    def _service_or_raise(self):
        if self._service is None:
            raise RuntimeError('Call authenticate() first')
        return self._service

    def _is_allowed_domain(self, email: str) -> bool:
        return settings.is_allowed_domain(email)

    def _parse_headers(self, headers: list[dict]) -> dict[str, str]:
        return {h['name'].lower(): h['value'] for h in headers}

    def _decode_body(self, payload: dict) -> str:
        """재귀적으로 이메일 본문(text/plain 우선) 추출."""
        mime = payload.get('mimeType', '')
        if mime == 'text/plain':
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
        elif mime.startswith('multipart/'):
            for part in payload.get('parts', []):
                text = self._decode_body(part)
                if text:
                    return text
        return ''

    async def fetch_recent(self, since: datetime | None = None) -> list[RawDocument]:
        svc = self._service_or_raise()
        query = 'in:inbox OR in:sent'
        if since:
            ts = int(since.timestamp())
            query += f' after:{ts}'

        docs: list[RawDocument] = []
        page_token: str | None = None
        thread_ids_seen: set[str] = set()

        while True:
            try:
                resp = svc.users().messages().list(
                    userId='me',
                    q=query,
                    pageToken=page_token,
                    maxResults=100,
                ).execute()
            except HttpError as exc:
                log.error('gmail.list_error', error=str(exc))
                break

            for msg_ref in resp.get('messages', []):
                msg_id = msg_ref['id']
                try:
                    msg = svc.users().messages().get(
                        userId='me', id=msg_id, format='full'
                    ).execute()
                except HttpError:
                    continue

                thread_id = msg.get('threadId', msg_id)
                # 스레드 중복 방지: 첫 메시지만 수집 후 스레드 단위로 묶음
                if thread_id in thread_ids_seen:
                    continue
                thread_ids_seen.add(thread_id)

                headers = self._parse_headers(msg.get('payload', {}).get('headers', []))
                sender = headers.get('from', '')
                to = headers.get('to', '')
                cc = headers.get('cc', '')
                bcc = headers.get('bcc', '')
                subject = headers.get('subject', '(no subject)')
                date_str = headers.get('date', '')

                # 회사 도메인 필터 — 발신자 또는 수신자 중 하나라도 허용 도메인이어야 수집
                all_emails = [sender] + [e.strip() for e in (to + ',' + cc + ',' + bcc).split(',') if e.strip()]
                if not any(self._is_allowed_domain(e) for e in all_emails):
                    continue

                body = self._decode_body(msg.get('payload', {}))
                body = _mask_pii(body)

                docs.append(RawDocument(
                    source_type='gmail',
                    source_id=msg_id,
                    source_url=f'https://mail.google.com/mail/u/0/#inbox/{msg_id}',
                    title=subject,
                    raw_content=body,
                    mime_type='text/plain',
                    metadata={
                        'thread_id': thread_id,
                        'from': sender,
                        'to': to,
                        'cc': cc,
                        'bcc': bcc,
                        'subject': subject,
                        'date': date_str,
                        'label_ids': msg.get('labelIds', []),
                    },
                ))

            page_token = resp.get('nextPageToken')
            if not page_token:
                break

        log.info('gmail.fetched', count=len(docs))
        return docs

    async def fetch_permissions(self, source_id: str) -> list[dict]:
        # Gmail 메시지는 발신자/수신자 관계가 권한 → 메타데이터에서 직접 추출
        return []

    async def fetch_thread(self, thread_id: str) -> list[RawDocument]:
        """스레드 전체 메시지 수집."""
        svc = self._service_or_raise()
        try:
            thread = svc.users().threads().get(userId='me', id=thread_id, format='full').execute()
        except HttpError as exc:
            log.error('gmail.thread_error', thread_id=thread_id, error=str(exc))
            return []

        docs = []
        for msg in thread.get('messages', []):
            headers = self._parse_headers(msg.get('payload', {}).get('headers', []))
            body = _mask_pii(self._decode_body(msg.get('payload', {})))
            docs.append(RawDocument(
                source_type='gmail',
                source_id=msg['id'],
                source_url=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                title=headers.get('subject', '(no subject)'),
                raw_content=body,
                mime_type='text/plain',
                metadata={
                    'thread_id': thread_id,
                    'from': headers.get('from', ''),
                    'to': headers.get('to', ''),
                    'cc': headers.get('cc', ''),
                    'date': headers.get('date', ''),
                },
            ))
        return docs
