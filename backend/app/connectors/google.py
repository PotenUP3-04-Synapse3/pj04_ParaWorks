import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx

from backend.app.connectors.base import ConnectorManifest, SourceEvent

GoogleQueryParams = dict[str, str | list[str]]

GOOGLE_CONNECTOR_SCOPES: dict[str, tuple[str, ...]] = {
    'gmail': ('https://www.googleapis.com/auth/gmail.readonly',),
    'drive': ('https://www.googleapis.com/auth/drive.readonly',),
    'calendar': ('https://www.googleapis.com/auth/calendar.readonly',),
}
GOOGLE_CONNECTOR_TYPES = frozenset(GOOGLE_CONNECTOR_SCOPES)


class GoogleApiClient(Protocol):
    def gmail_messages(self, *, after_internal_date: str | None = None) -> list[dict]:
        raise NotImplementedError

    def drive_files(self, *, modified_after: str | None = None) -> list[dict]:
        raise NotImplementedError

    def calendar_events(self) -> list[dict]:
        raise NotImplementedError


class GoogleApiError(RuntimeError):
    pass


class GoogleWebApiClient:
    def __init__(
        self,
        *,
        oauth_token: str,
        http_client: httpx.Client | None = None,
        gmail_base_url: str = 'https://gmail.googleapis.com',
        drive_base_url: str = 'https://www.googleapis.com',
        calendar_base_url: str = 'https://www.googleapis.com',
        page_limit: int = 100,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.oauth_token = oauth_token
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.gmail_base_url = gmail_base_url.rstrip('/')
        self.drive_base_url = drive_base_url.rstrip('/')
        self.calendar_base_url = calendar_base_url.rstrip('/')
        self.page_limit = page_limit
        self.max_retries = max_retries
        self.sleep = sleep

    def gmail_messages(self, *, after_internal_date: str | None = None) -> list[dict]:
        messages: list[dict] = []
        params: GoogleQueryParams = {'maxResults': str(self.page_limit)}
        if after_internal_date:
            params['q'] = _gmail_after_query(after_internal_date)
        for message_ref in self._get_paged_items(
            f'{self.gmail_base_url}/gmail/v1/users/me/messages',
            item_key='messages',
            params=params,
        ):
            message_id = str(message_ref['id'])
            messages.append(
                self._get_json(
                    f'{self.gmail_base_url}/gmail/v1/users/me/messages/{message_id}',
                    params={
                        'format': 'metadata',
                        'metadataHeaders': ['Subject', 'From', 'Date'],
                    },
                )
            )
        return messages

    def drive_files(self, *, modified_after: str | None = None) -> list[dict]:
        params: GoogleQueryParams = {
            'pageSize': str(self.page_limit),
            'fields': 'nextPageToken,files(id,name,mimeType,webViewLink,modifiedTime,owners)',
        }
        if modified_after:
            params['q'] = f"modifiedTime > '{modified_after}'"
        return self._get_paged_items(
            f'{self.drive_base_url}/drive/v3/files',
            item_key='files',
            params=params,
        )

    def calendar_events(self) -> list[dict]:
        payload = self._get_json(
            f'{self.calendar_base_url}/calendar/v3/calendars/primary/events',
            params={
                'maxResults': str(self.page_limit),
                'singleEvents': 'true',
                'orderBy': 'updated',
            },
        )
        return list(payload.get('items', []))

    def _get_json(self, url: str, *, params: GoogleQueryParams) -> dict:
        for attempt in range(self.max_retries + 1):
            response = self.http_client.get(
                url,
                headers={'Authorization': f'Bearer {self.oauth_token}'},
                params=params,
            )
            if response.status_code < 400:
                return response.json()
            if not _should_retry(response.status_code):
                raise GoogleApiError(_google_error_message(response))
            if attempt >= self.max_retries:
                if response.status_code == 429:
                    raise GoogleApiError('Google API request failed: rate_limited')
                raise GoogleApiError(f'Google API request failed: http_{response.status_code}')
            self.sleep(_retry_after_seconds(response))
        raise GoogleApiError('Google API request failed')

    def _get_paged_items(self, url: str, *, item_key: str, params: GoogleQueryParams) -> list[dict]:
        items: list[dict] = []
        page_token: str | None = None
        while True:
            page_params = dict(params)
            if page_token:
                page_params['pageToken'] = page_token
            payload = self._get_json(url, params=page_params)
            items.extend(payload.get(item_key, []))
            page_token = payload.get('nextPageToken')
            if not page_token:
                return items


@dataclass(frozen=True)
class GoogleConnectorConfig:
    connector_type: str
    oauth_token: str
    account_id: str
    account_name: str


@dataclass(frozen=True)
class GoogleConnector:
    config: GoogleConnectorConfig
    client: GoogleApiClient

    @property
    def source_type(self) -> str:
        return self.config.connector_type

    @property
    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type=self.config.connector_type,
            display_name=_display_name(self.config.connector_type),
            mode='live',
            auth_type='oauth',
            required_scopes=GOOGLE_CONNECTOR_SCOPES[self.config.connector_type],
            sync_strategy='incremental',
            cost_policy='Fetch Google source deltas before agent or embedding work.',
        )

    def fetch_events(self) -> list[SourceEvent]:
        if self.config.connector_type == 'gmail':
            return [self._gmail_message_to_source_event(message) for message in self.client.gmail_messages()]
        if self.config.connector_type == 'drive':
            return [self._drive_file_to_source_event(file) for file in self.client.drive_files()]
        if self.config.connector_type == 'calendar':
            return [self._calendar_event_to_source_event(event) for event in self.client.calendar_events()]
        raise GoogleApiError(f'Unsupported Google connector: {self.config.connector_type}')

    def fetch_events_since(self, latest_cursors_by_partition: dict[str, str]) -> list[SourceEvent]:
        if self.config.connector_type == 'gmail':
            return [
                self._gmail_message_to_source_event(message)
                for message in self.client.gmail_messages(
                    after_internal_date=latest_cursors_by_partition.get('gmail')
                )
            ]
        if self.config.connector_type == 'drive':
            return [
                self._drive_file_to_source_event(file)
                for file in self.client.drive_files(modified_after=latest_cursors_by_partition.get('drive'))
            ]
        return self.fetch_events()

    def _gmail_message_to_source_event(self, message: dict) -> SourceEvent:
        message_id = str(message['id'])
        subject = _header_value(message, 'Subject') or f'Gmail message {message_id}'
        author = _header_value(message, 'From') or self.config.account_name
        snippet = str(message.get('snippet') or '')
        return SourceEvent(
            source_type='gmail',
            source_id=f'gmail:{message_id}',
            source_url=f'https://mail.google.com/mail/u/0/#all/{message_id}',
            title=subject,
            body=f'{subject}\n\n{snippet}'.strip(),
            author=author,
            participants=[author] if author else [],
            timestamp=_timestamp_from_google_millis(message.get('internalDate')),
            permission_level='internal',
            raw_metadata={
                'message_id': message_id,
                'account_id': self.config.account_id,
                'sync_partition': 'gmail',
                'sync_cursor': str(message.get('internalDate') or ''),
                'required_scopes': list(GOOGLE_CONNECTOR_SCOPES['gmail']),
            },
        )

    def _drive_file_to_source_event(self, file: dict) -> SourceEvent:
        file_id = str(file['id'])
        title = str(file.get('name') or f'Drive file {file_id}')
        author = _first_owner_email(file) or self.config.account_name
        modified_time = str(file.get('modifiedTime') or '')
        return SourceEvent(
            source_type='drive',
            source_id=f'drive:{file_id}',
            source_url=str(file.get('webViewLink') or f'https://drive.google.com/file/d/{file_id}/view'),
            title=title,
            body=f'Google Drive file changed: {title}',
            author=author,
            participants=[author] if author else [],
            timestamp=_timestamp_from_iso(modified_time),
            permission_level='restricted',
            raw_metadata={
                'file_id': file_id,
                'mime_type': file.get('mimeType'),
                'account_id': self.config.account_id,
                'sync_partition': 'drive',
                'sync_cursor': modified_time,
                'required_scopes': list(GOOGLE_CONNECTOR_SCOPES['drive']),
            },
        )

    def _calendar_event_to_source_event(self, event: dict) -> SourceEvent:
        event_id = str(event['id'])
        title = str(event.get('summary') or f'Calendar event {event_id}')
        author = str((event.get('creator') or {}).get('email') or self.config.account_name)
        participants = [
            str(attendee['email'])
            for attendee in event.get('attendees', [])
            if attendee.get('email')
        ]
        if author and author not in participants:
            participants.insert(0, author)
        return SourceEvent(
            source_type='calendar',
            source_id=f'calendar:{event_id}',
            source_url=str(event.get('htmlLink') or 'https://calendar.google.com'),
            title=title,
            body=str(event.get('description') or title),
            author=author,
            participants=participants,
            timestamp=_timestamp_from_iso(event.get('updated')),
            permission_level='internal',
            raw_metadata={
                'event_id': event_id,
                'account_id': self.config.account_id,
                'required_scopes': list(GOOGLE_CONNECTOR_SCOPES['calendar']),
            },
        )


def _google_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f'Google API request failed with {response.status_code}'
    error = payload.get('error') or {}
    if isinstance(error, dict):
        return str(error.get('message') or f'Google API request failed with {response.status_code}')
    return str(error)


def _gmail_after_query(after_internal_date: str) -> str:
    return f'after:{int(int(after_internal_date) / 1000)}'


def _should_retry(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _retry_after_seconds(response: httpx.Response) -> float:
    retry_after = response.headers.get('Retry-After')
    if not retry_after:
        return 1.0
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        return 1.0


def _display_name(connector_type: str) -> str:
    if connector_type == 'gmail':
        return 'Gmail'
    if connector_type == 'drive':
        return 'Google Drive'
    if connector_type == 'calendar':
        return 'Google Calendar'
    return connector_type


def _header_value(message: dict, name: str) -> str | None:
    headers = (message.get('payload') or {}).get('headers') or []
    for header in headers:
        if str(header.get('name', '')).lower() == name.lower():
            return str(header.get('value') or '')
    return None


def _first_owner_email(file: dict) -> str | None:
    owners = file.get('owners') or []
    if not owners:
        return None
    return owners[0].get('emailAddress')


def _timestamp_from_google_millis(value: object) -> datetime:
    if value is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(int(str(value)) / 1000, tz=UTC)


def _timestamp_from_iso(value: object) -> datetime:
    if not value:
        return datetime.now(UTC)
    normalized = str(value).replace('Z', '+00:00')
    return datetime.fromisoformat(normalized).astimezone(UTC)
