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
    def __init__(self) -> None:
        self.gmail_after_internal_date: str | None = None
        self.drive_modified_after: str | None = None

    def gmail_messages(self, *, after_internal_date: str | None = None) -> list[dict]:
        self.gmail_after_internal_date = after_internal_date
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

    def drive_files(self, *, modified_after: str | None = None) -> list[dict]:
        self.drive_modified_after = modified_after
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
    assert event.raw_metadata['sync_partition'] == 'gmail'
    assert event.raw_metadata['sync_cursor'] == '1777600800000'


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
    assert event.raw_metadata['sync_partition'] == 'drive'
    assert event.raw_metadata['sync_cursor'] == '2026-05-01T09:00:00Z'


def test_google_connector_fetches_gmail_events_since_latest_cursor() -> None:
    client = FakeGoogleClient()
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='gmail',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    )

    events = connector.fetch_events_since({'gmail': '1777600800000'})

    assert len(events) == 1
    assert client.gmail_after_internal_date == '1777600800000'


def test_google_connector_fetches_drive_events_since_latest_cursor() -> None:
    client = FakeGoogleClient()
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='drive',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    )

    events = connector.fetch_events_since({'drive': '2026-05-01T09:00:00Z'})

    assert len(events) == 1
    assert client.drive_modified_after == '2026-05-01T09:00:00Z'


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
        if request.url.path == '/gmail/v1/users/me/messages/msg-1':
            return httpx.Response(200, json={'id': 'msg-1'})
        return httpx.Response(200, json={'messages': [{'id': 'msg-1'}]})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.gmail_messages() == [{'id': 'msg-1'}]
    assert requests[0].url.path == '/gmail/v1/users/me/messages'
    assert requests[1].url.path == '/gmail/v1/users/me/messages/msg-1'


def test_google_web_api_client_paginates_and_hydrates_gmail_messages() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == '/gmail/v1/users/me/messages' and request.url.params.get('pageToken') is None:
            return httpx.Response(200, json={'messages': [{'id': 'msg-1'}], 'nextPageToken': 'page-2'})
        if request.url.path == '/gmail/v1/users/me/messages' and request.url.params.get('pageToken') == 'page-2':
            return httpx.Response(200, json={'messages': [{'id': 'msg-2'}]})
        if request.url.path == '/gmail/v1/users/me/messages/msg-1':
            return httpx.Response(
                200,
                json={
                    'id': 'msg-1',
                    'snippet': 'first detail',
                    'payload': {'headers': [{'name': 'Subject', 'value': 'First'}]},
                },
            )
        if request.url.path == '/gmail/v1/users/me/messages/msg-2':
            return httpx.Response(
                200,
                json={
                    'id': 'msg-2',
                    'snippet': 'second detail',
                    'payload': {'headers': [{'name': 'Subject', 'value': 'Second'}]},
                },
            )
        raise AssertionError(f'unexpected request: {request.url}')

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        page_limit=1,
    )

    messages = client.gmail_messages()

    assert [message['id'] for message in messages] == ['msg-1', 'msg-2']
    assert messages[0]['payload']['headers'][0]['value'] == 'First'
    assert messages[1]['snippet'] == 'second detail'
    request_paths = [request.url.path for request in requests]
    assert request_paths.count('/gmail/v1/users/me/messages') == 2
    assert '/gmail/v1/users/me/messages/msg-1' in request_paths
    assert '/gmail/v1/users/me/messages/msg-2' in request_paths
    assert any(request.url.params.get('pageToken') == 'page-2' for request in requests)
    detail_request = next(request for request in requests if request.url.path == '/gmail/v1/users/me/messages/msg-1')
    assert detail_request.url.params.get_list('metadataHeaders') == ['Subject', 'From', 'Date']


def test_google_web_api_client_paginates_drive_files() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.params.get('pageToken') is None:
            return httpx.Response(
                200,
                json={
                    'files': [{'id': 'file-1', 'name': 'First'}],
                    'nextPageToken': 'drive-page-2',
                },
            )
        return httpx.Response(200, json={'files': [{'id': 'file-2', 'name': 'Second'}]})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        page_limit=1,
    )

    files = client.drive_files()

    assert [file['id'] for file in files] == ['file-1', 'file-2']
    assert requests[0].url.path == '/drive/v3/files'
    assert requests[1].url.params['pageToken'] == 'drive-page-2'


def test_google_web_api_client_sends_delta_params_for_gmail_and_drive() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == '/gmail/v1/users/me/messages':
            return httpx.Response(200, json={'messages': []})
        if request.url.path == '/drive/v3/files':
            return httpx.Response(200, json={'files': []})
        raise AssertionError(f'unexpected request: {request.url}')

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.gmail_messages(after_internal_date='1777600800000') == []
    assert client.drive_files(modified_after='2026-05-01T09:00:00Z') == []

    gmail_request = next(request for request in requests if request.url.path == '/gmail/v1/users/me/messages')
    drive_request = next(request for request in requests if request.url.path == '/drive/v3/files')
    assert gmail_request.url.params['q'] == 'after:1777600800'
    assert drive_request.url.params['q'] == "modifiedTime > '2026-05-01T09:00:00Z'"


def test_google_web_api_client_retries_rate_limited_requests_with_retry_after() -> None:
    requests: list[httpx.Request] = []
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={'Retry-After': '2'}, json={'error': {'message': 'rate limit'}})
        return httpx.Response(200, json={'files': []})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleep_calls.append,
    )

    assert client.drive_files() == []
    assert len(requests) == 2
    assert sleep_calls == [2.0]


def test_google_web_api_client_stops_retrying_rate_limited_requests_after_limit() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(429, json={'error': {'message': 'rate limit'}})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=1,
        sleep=lambda seconds: None,
    )

    with pytest.raises(GoogleApiError, match='rate_limited'):
        client.drive_files()
    assert len(requests) == 2


def test_google_web_api_client_raises_clear_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={'error': {'message': 'missing scope'}})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(GoogleApiError, match='missing scope'):
        client.gmail_messages()
