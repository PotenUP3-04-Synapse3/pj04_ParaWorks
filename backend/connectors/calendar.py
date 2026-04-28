from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.connectors.base import BaseConnector, RawDocument
from backend.core.config import settings

log = structlog.get_logger(__name__)


def _build_credentials():
    sa_json = settings.google_service_account_json
    if os.path.exists(sa_json):
        creds = service_account.Credentials.from_service_account_file(
            sa_json,
            scopes=['https://www.googleapis.com/auth/calendar.readonly'],
        )
    else:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/calendar.readonly'],
        )
    return creds.with_subject(settings.google_subject_email)


class GoogleCalendarConnector(BaseConnector):
    def __init__(self):
        self._service = None

    async def authenticate(self) -> None:
        creds = _build_credentials()
        self._service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        log.info('google_calendar.authenticated')

    def _service_or_raise(self):
        if self._service is None:
            raise RuntimeError('Call authenticate() first')
        return self._service

    async def fetch_recent(self, since: datetime | None = None) -> list[RawDocument]:
        svc = self._service_or_raise()
        time_min = (since or datetime.now(timezone.utc)).isoformat()

        docs: list[RawDocument] = []
        page_token: str | None = None
        try:
            while True:
                resp = svc.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    maxResults=250,
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token,
                ).execute()

                for event in resp.get('items', []):
                    summary = event.get('summary', '(no title)')
                    description = event.get('description', '')
                    start = event.get('start', {})
                    attendees = event.get('attendees', [])
                    attachments = event.get('attachments', [])

                    start_dt = start.get('dateTime') or start.get('date', '')
                    content = f'제목: {summary}\n\n참석자:\n'
                    for a in attendees:
                        content += f"  - {a.get('email', '')} ({a.get('responseStatus', '')})\n"
                    if description:
                        content += f'\n내용:\n{description}'
                    if attachments:
                        content += '\n첨부파일:\n' + '\n'.join(
                            f"  - {att.get('title', '')} ({att.get('fileUrl', '')})"
                            for att in attachments
                        )

                    docs.append(RawDocument(
                        source_type='calendar',
                        source_id=event['id'],
                        source_url=event.get('htmlLink'),
                        title=summary,
                        raw_content=content,
                        mime_type='text/plain',
                        metadata={
                            'event_id': event['id'],
                            'start': start_dt,
                            'end': (event.get('end', {}).get('dateTime') or event.get('end', {}).get('date', '')),
                            'organizer': event.get('organizer', {}).get('email', ''),
                            'attendees': [a.get('email', '') for a in attendees],
                            'attachments': [att.get('fileId') for att in attachments if att.get('fileId')],
                        },
                    ))

                page_token = resp.get('nextPageToken')
                if not page_token:
                    break
        except HttpError as exc:
            log.error('google_calendar.fetch_error', error=str(exc))

        log.info('google_calendar.fetched', count=len(docs))
        return docs

    async def fetch_permissions(self, source_id: str) -> list[dict]:
        return []  # Calendar 이벤트는 참석자 목록이 권한
