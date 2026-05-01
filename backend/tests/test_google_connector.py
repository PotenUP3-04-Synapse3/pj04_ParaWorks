from datetime import UTC, datetime

import httpx
import pytest

from backend.app.connectors.google import (
    GOOGLE_CONNECTOR_SCOPES,
    GoogleApiError,
    GoogleConnector,
    GoogleConnectorConfig,
    GoogleWebApiClient,
)


class FakeGoogleClient:
    def gmail_messages(self) -> list[dict]:
        return [
            {
                'id': 'msg-1',
                'snippet': '계약 검토 일정은 금요일까지 확정합니다.',
                'internalDate': '1777600800000',
                'payload': {
                    'headers': [
                        {'name': 'Subject', 'value': '계약 검토 일정'},
                        {'name': 'From', 'value': 'min@example.com'},
                    ]
                },
            }
        ]

    def drive_files(self) -> list[dict]:
        return [
            {
                'id': 'file-1',
                'name': '사업계획서',
                'mimeType': 'application/vnd.google-apps.document',
                'webViewLink': 'https://drive.google.com/file/d/file-1/view',
                'modifiedTime': '2026-05-01T09:00:00Z',
                'owners': [{'emailAddress': 'owner@example.com'}],
            }
        ]

    def calendar_events(self) -> list[dict]:
        return [
            {
                'id': 'event-1',
                'summary': 'PM 회의',
                'description': '런칭 일정 점검',
                'htmlLink': 'https://calendar.google.com/event?eid=event-1',
                'updated': '2026-05-01T10:00:00Z',
                'creator': {'email': 'pm@example.com'},
                'attendees': [{'email': 'pm@example.com'}, {'email': 'dev@example.com'}],
            }
        ]


def test_google_connector_maps_gmail_messages_to_source_events() -> None:
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='gmail',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=FakeGoogleClient(),
    )

    events = connector.fetch_events()

    assert len(events) == 1
    event = events[0]
    assert event.source_type == 'gmail'
    assert event.source_id == 'gmail:msg-1'
    assert event.source_url == 'https://mail.google.com/mail/u/0/#all/msg-1'
    assert event.title == '계약 검토 일정'
    assert event.body == '계약 검토 일정\n\n계약 검토 일정은 금요일까지 확정합니다.'
    assert event.author == 'min@example.com'
    assert event.participants == ['min@example.com']
    assert event.timestamp == datetime.fromtimestamp(1777600800, tz=UTC)
    assert event.permission_level == 'internal'
    assert event.raw_metadata['required_scopes'] == list(GOOGLE_CONNECTOR_SCOPES['gmail'])


def test_google_connector_maps_drive_files_to_source_events() -> None:
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='drive',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=FakeGoogleClient(),
    )

    events = connector.fetch_events()

    assert len(events) == 1
    event = events[0]
    assert event.source_type == 'drive'
    assert event.source_id == 'drive:file-1'
    assert event.source_url == 'https://drive.google.com/file/d/file-1/view'
    assert event.title == '사업계획서'
    assert 'Google Drive file changed: 사업계획서' in event.body
    assert event.author == 'owner@example.com'
    assert event.timestamp == datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    assert event.raw_metadata['mime_type'] == 'application/vnd.google-apps.document'


def test_google_connector_maps_calendar_events_to_source_events() -> None:
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='calendar',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=FakeGoogleClient(),
    )

    events = connector.fetch_events()

    assert len(events) == 1
    event = events[0]
    assert event.source_type == 'calendar'
    assert event.source_id == 'calendar:event-1'
    assert event.source_url == 'https://calendar.google.com/event?eid=event-1'
    assert event.title == 'PM 회의'
    assert event.body == '런칭 일정 점검'
    assert event.author == 'pm@example.com'
    assert event.participants == ['pm@example.com', 'dev@example.com']
    assert event.timestamp == datetime(2026, 5, 1, 10, 0, tzinfo=UTC)


def test_google_web_api_client_attaches_bearer_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers['authorization'] == 'Bearer google-oauth-token'
        return httpx.Response(200, json={'messages': [{'id': 'msg-1'}]})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.gmail_messages() == [{'id': 'msg-1'}]
    assert requests[0].url.path == '/gmail/v1/users/me/messages'


def test_google_web_api_client_raises_clear_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={'error': {'message': 'missing scope'}})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(GoogleApiError, match='missing scope'):
        client.gmail_messages()
