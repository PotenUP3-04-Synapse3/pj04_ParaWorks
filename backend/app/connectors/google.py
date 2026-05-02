import base64
import binascii
import html
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx

from backend.app.connectors.base import ConnectorManifest, SourceEvent

GoogleQueryParams = dict[str, str | list[str]]
GOOGLE_TEXT_BODY_LIMIT = 4_000

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

    def calendar_events(self, *, updated_min: str | None = None) -> list[dict]:
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
                    params={'format': 'full'},
                )
            )
        return messages

    def drive_files(self, *, modified_after: str | None = None) -> list[dict]:
        params: GoogleQueryParams = {
            'pageSize': str(self.page_limit),
            'fields': (
                'nextPageToken,'
                'files(id,name,description,mimeType,webViewLink,createdTime,modifiedTime,owners,'
                'lastModifyingUser(emailAddress,displayName))'
            ),
        }
        if modified_after:
            params['q'] = f"modifiedTime > '{modified_after}'"
        return self._get_paged_items(
            f'{self.drive_base_url}/drive/v3/files',
            item_key='files',
            params=params,
        )

    def calendar_events(self, *, updated_min: str | None = None) -> list[dict]:
        params: GoogleQueryParams = {
            'maxResults': str(self.page_limit),
            'singleEvents': 'true',
            'orderBy': 'updated',
        }
        if updated_min:
            params['updatedMin'] = updated_min
        return self._get_paged_items(
            f'{self.calendar_base_url}/calendar/v3/calendars/primary/events',
            item_key='items',
            params=params,
        )

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
        if self.config.connector_type == 'calendar':
            return [
                self._calendar_event_to_source_event(event)
                for event in self.client.calendar_events(updated_min=latest_cursors_by_partition.get('calendar'))
            ]
        return self.fetch_events()

    def _gmail_message_to_source_event(self, message: dict) -> SourceEvent:
        message_id = str(message['id'])
        subject = _header_value(message, 'Subject') or f'Gmail message {message_id}'
        author = _header_value(message, 'From') or self.config.account_name
        date_header = _header_value(message, 'Date')
        snippet = str(message.get('snippet') or '')
        extracted_body = _gmail_text_body(message)
        source_body = extracted_body or snippet
        body_text, body_truncated = _bounded_text(source_body)
        body_source = 'payload' if extracted_body else 'snippet'
        header_lines = [f'From: {author}'] if author else []
        if date_header:
            header_lines.append(f'Date: {date_header}')
        return SourceEvent(
            source_type='gmail',
            source_id=f'gmail:{message_id}',
            source_url=f'https://mail.google.com/mail/u/0/#all/{message_id}',
            title=subject,
            body='\n\n'.join(part for part in [subject, '\n'.join(header_lines), body_text] if part).strip(),
            author=author,
            participants=[author] if author else [],
            timestamp=_timestamp_from_google_millis(message.get('internalDate')),
            permission_level='internal',
            raw_metadata={
                'message_id': message_id,
                'thread_id': message.get('threadId'),
                'label_ids': message.get('labelIds') or [],
                'date_header': date_header,
                'account_id': self.config.account_id,
                'sync_partition': 'gmail',
                'sync_cursor': str(message.get('internalDate') or ''),
                'body_source': body_source,
                'body_truncated': body_truncated,
                'required_scopes': list(GOOGLE_CONNECTOR_SCOPES['gmail']),
            },
        )

    def _drive_file_to_source_event(self, file: dict) -> SourceEvent:
        file_id = str(file['id'])
        title = str(file.get('name') or f'Drive file {file_id}')
        author = _first_owner_email(file) or self.config.account_name
        modified_time = str(file.get('modifiedTime') or '')
        description = str(file.get('description') or '')
        last_modifying_user_email = str((file.get('lastModifyingUser') or {}).get('emailAddress') or '')
        body_lines = [
            f'Google Drive file changed: {title}',
            f'Mime type: {file.get("mimeType")}' if file.get('mimeType') else '',
            f'Description: {description}' if description else '',
            f'Owner: {author}' if author else '',
            f'Last modifier: {last_modifying_user_email}' if last_modifying_user_email else '',
            f'Modified: {modified_time}' if modified_time else '',
        ]
        return SourceEvent(
            source_type='drive',
            source_id=f'drive:{file_id}',
            source_url=str(file.get('webViewLink') or f'https://drive.google.com/file/d/{file_id}/view'),
            title=title,
            body='\n'.join(line for line in body_lines if line),
            author=author,
            participants=[author] if author else [],
            timestamp=_timestamp_from_iso(modified_time),
            permission_level='restricted',
            raw_metadata={
                'file_id': file_id,
                'mime_type': file.get('mimeType'),
                'description': description,
                'created_time': file.get('createdTime'),
                'modified_time': modified_time,
                'last_modifying_user_email': last_modifying_user_email,
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
        updated = str(event.get('updated') or '')
        description = str(event.get('description') or '')
        location = str(event.get('location') or '')
        start = _calendar_time_value(event.get('start'))
        end = _calendar_time_value(event.get('end'))
        participants = [
            str(attendee['email'])
            for attendee in event.get('attendees', [])
            if attendee.get('email')
        ]
        if author and author not in participants:
            participants.insert(0, author)
        body_lines = [
            title,
            '',
            f'Description: {description}' if description else '',
            f'Location: {location}' if location else '',
            f'Start: {start}' if start else '',
            f'End: {end}' if end else '',
        ]
        return SourceEvent(
            source_type='calendar',
            source_id=f'calendar:{event_id}',
            source_url=str(event.get('htmlLink') or 'https://calendar.google.com'),
            title=title,
            body='\n'.join(line for line in body_lines if line or line == '').strip(),
            author=author,
            participants=participants,
            timestamp=_timestamp_from_iso(updated),
            permission_level='internal',
            raw_metadata={
                'event_id': event_id,
                'location': location,
                'start': start,
                'end': end,
                'attendee_count': len(participants),
                'account_id': self.config.account_id,
                'sync_partition': 'calendar',
                'sync_cursor': updated,
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


def _gmail_text_body(message: dict) -> str:
    payload = message.get('payload') or {}
    candidates = _gmail_payload_text_candidates(payload)
    if not candidates:
        return ''
    plain_text = [text for mime_type, text in candidates if mime_type == 'text/plain' and text]
    if plain_text:
        return _normalize_text('\n\n'.join(plain_text))
    html_text = [text for mime_type, text in candidates if mime_type == 'text/html' and text]
    if html_text:
        return _normalize_text(_strip_html('\n\n'.join(html_text)))
    return _normalize_text(candidates[0][1])


def _gmail_payload_text_candidates(payload: dict) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    mime_type = str(payload.get('mimeType') or '')
    data = (payload.get('body') or {}).get('data')
    if isinstance(data, str) and mime_type.startswith('text/'):
        decoded = _decode_base64url(data)
        if decoded:
            candidates.append((mime_type, decoded))
    for part in payload.get('parts') or []:
        candidates.extend(_gmail_payload_text_candidates(part))
    return candidates


def _decode_base64url(value: str) -> str:
    padded = value + '=' * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8', errors='replace')
    except (binascii.Error, ValueError):
        return ''


def _strip_html(value: str) -> str:
    without_tags = re.sub(r'<[^>]+>', ' ', value)
    return html.unescape(without_tags)


def _normalize_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def _bounded_text(value: str, limit: int = GOOGLE_TEXT_BODY_LIMIT) -> tuple[str, bool]:
    normalized = _normalize_text(value)
    if len(normalized) <= limit:
        return normalized, False
    return normalized[:limit].rstrip(), True


def _first_owner_email(file: dict) -> str | None:
    owners = file.get('owners') or []
    if not owners:
        return None
    return owners[0].get('emailAddress')


def _calendar_time_value(value: object) -> str:
    if not isinstance(value, dict):
        return ''
    return str(value.get('dateTime') or value.get('date') or '')


def _timestamp_from_google_millis(value: object) -> datetime:
    if value is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(int(str(value)) / 1000, tz=UTC)


def _timestamp_from_iso(value: object) -> datetime:
    if not value:
        return datetime.now(UTC)
    normalized = str(value).replace('Z', '+00:00')
    return datetime.fromisoformat(normalized).astimezone(UTC)
