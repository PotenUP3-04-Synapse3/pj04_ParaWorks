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
    def __init__(
        self,
        drive_files: list[dict] | None = None,
        drive_exports: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.gmail_after_internal_date: str | None = None
        self.drive_modified_after: str | None = None
        self.calendar_updated_min: str | None = None
        self.drive_export_requests: list[tuple[str, str]] = []
        self._drive_files = drive_files
        self._drive_exports = drive_exports or {}

    def gmail_messages(self, *, after_internal_date: str | None = None) -> list[dict]:
        self.gmail_after_internal_date = after_internal_date
        return [
            {
                'id': 'msg-1',
                'threadId': 'thread-1',
                'labelIds': ['INBOX', 'IMPORTANT'],
                'snippet': '계약 검토 일정은 금요일까지 확정합니다.',
                'internalDate': '1777600800000',
                'payload': {
                    'mimeType': 'multipart/alternative',
                    'headers': [
                        {'name': 'Subject', 'value': '계약 검토 일정'},
                        {'name': 'From', 'value': 'min@example.com'},
                        {'name': 'To', 'value': 'para@example.com'},
                        {'name': 'Cc', 'value': 'partner@client.co.kr'},
                        {'name': 'Date', 'value': 'Fri, 1 May 2026 10:00:00 +0900'},
                    ],
                    'parts': [
                        {
                            'mimeType': 'text/html',
                            'body': {'data': 'PGI-SFRNTDw_Yj4'},
                        },
                        {
                            'mimeType': 'text/plain',
                            'body': {
                                'data': '6rOE7JW9IOqygO2GoCDsnbzsoJXsnYAg6riI7JqU7J286rmM7KeAIO2Zleygle2VqeuLiOuLpC4',
                            },
                        },
                    ]
                },
            }
        ]

    def drive_files(self, *, modified_after: str | None = None) -> list[dict]:
        self.drive_modified_after = modified_after
        if self._drive_files is not None:
            return self._drive_files
        return [
            {
                'id': 'file-1',
                'name': '사업계획서',
                'mimeType': 'application/vnd.google-apps.document',
                'description': '2026년 상반기 매출 목표와 채용 계획',
                'webViewLink': 'https://drive.google.com/file/d/file-1/view',
                'modifiedTime': '2026-05-01T09:00:00Z',
                'createdTime': '2026-04-30T09:00:00Z',
                'version': '42',
                'headRevisionId': 'rev-42',
                'owners': [{'emailAddress': 'owner@example.com'}],
                'lastModifyingUser': {'emailAddress': 'editor@example.com'},
            }
        ]

    def drive_file_text_export(self, *, file_id: str, export_mime_type: str) -> str:
        self.drive_export_requests.append((file_id, export_mime_type))
        if (file_id, export_mime_type) in self._drive_exports:
            return self._drive_exports[(file_id, export_mime_type)]
        return '휴가 신청은 HR 시스템에서 진행합니다.\n승인은 팀장이 검토합니다.'

    def calendar_events(self, *, updated_min: str | None = None) -> list[dict]:
        self.calendar_updated_min = updated_min
        return [
            {
                'id': 'event-1',
                'summary': 'PM 회의',
                'description': '런칭 일정 점검',
                'location': '회의실 A',
                'htmlLink': 'https://calendar.google.com/event?eid=event-1',
                'status': 'confirmed',
                'updated': '2026-05-01T10:00:00Z',
                'start': {'dateTime': '2026-05-02T09:00:00+09:00'},
                'end': {'dateTime': '2026-05-02T10:00:00+09:00'},
                'organizer': {'email': 'lead@example.com'},
                'creator': {'email': 'pm@example.com'},
                'attendees': [
                    {'email': 'pm@example.com', 'responseStatus': 'accepted'},
                    {'email': 'dev@example.com', 'responseStatus': 'needsAction'},
                    {'email': 'client@customer.co.kr', 'responseStatus': 'declined'},
                ],
                'recurringEventId': 'series-1',
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
    assert event.body == '계약 검토 일정\n\nFrom: min@example.com\nDate: Fri, 1 May 2026 10:00:00 +0900\n\n계약 검토 일정은 금요일까지 확정합니다.'
    assert event.author == 'min@example.com'
    assert event.participants == ['min@example.com', 'para@example.com', 'partner@client.co.kr']
    assert event.timestamp == datetime.fromtimestamp(1777600800, tz=UTC)
    assert event.permission_level == 'internal'
    assert event.raw_metadata['required_scopes'] == list(GOOGLE_CONNECTOR_SCOPES['gmail'])
    assert event.raw_metadata['sync_partition'] == 'gmail'
    assert event.raw_metadata['sync_cursor'] == '1777600800000'
    assert event.raw_metadata['thread_id'] == 'thread-1'
    assert event.raw_metadata['thread_context_key'] == 'thread-1:msg-1'
    assert event.raw_metadata['label_ids'] == ['INBOX', 'IMPORTANT']
    assert event.raw_metadata['from_domain'] == 'example.com'
    assert event.raw_metadata['participant_domains'] == ['client.co.kr', 'example.com']
    assert event.raw_metadata['external_domains'] == ['client.co.kr']
    assert event.raw_metadata['has_external_participants'] is True
    assert event.raw_metadata['body_source'] == 'payload'
    assert event.raw_metadata['body_truncated'] is False


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
    assert event.body == '휴가 신청은 HR 시스템에서 진행합니다.\n승인은 팀장이 검토합니다.'
    assert event.author == 'owner@example.com'
    assert event.timestamp == datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    assert event.raw_metadata['mime_type'] == 'application/vnd.google-apps.document'
    assert event.raw_metadata['sync_partition'] == 'drive'
    assert event.raw_metadata['sync_cursor'] == '2026-05-01T09:00:00Z'
    assert event.raw_metadata['description'] == '2026년 상반기 매출 목표와 채용 계획'
    assert event.raw_metadata['created_time'] == '2026-04-30T09:00:00Z'
    assert event.raw_metadata['last_modifying_user_email'] == 'editor@example.com'
    assert event.raw_metadata['parser_name'] == 'google_drive_text_export'
    assert event.raw_metadata['parser_status'] == 'parsed'
    assert event.raw_metadata['parser_status_reason'] is None
    assert event.raw_metadata['document_version'] == '42'
    assert event.raw_metadata['revision_id'] == 'rev-42'
    assert event.raw_metadata['content_signature'] == 'drive:file-1:42:rev-42'


def test_google_connector_exports_google_docs_text_into_drive_source_events() -> None:
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

    event = connector.fetch_events()[0]

    assert client.drive_export_requests == [('file-1', 'text/plain')]
    assert event.body == '휴가 신청은 HR 시스템에서 진행합니다.\n승인은 팀장이 검토합니다.'
    assert event.permission_level == 'restricted'
    assert event.raw_metadata['parser_name'] == 'google_drive_text_export'
    assert event.raw_metadata['parser_status'] == 'parsed'
    assert event.raw_metadata['parser_status_reason'] is None
    assert event.raw_metadata['source_snippet'] == '휴가 신청은 HR 시스템에서 진행합니다. 승인은 팀장이 검토합니다.'


def test_google_connector_exports_google_sheets_csv_into_drive_source_events() -> None:
    client = FakeGoogleClient(
        drive_files=[
            {
                'id': 'sheet-1',
                'name': '비용 정산표',
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'webViewLink': 'https://drive.google.com/file/d/sheet-1/view',
                'modifiedTime': '2026-05-01T09:00:00Z',
                'version': '7',
                'headRevisionId': 'sheet-rev-7',
                'owners': [{'emailAddress': 'owner@example.com'}],
            }
        ],
        drive_exports={
            ('sheet-1', 'text/csv'): '항목,금액\n출장비,120000\n식대,45000',
        },
    )
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='drive',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    )

    event = connector.fetch_events()[0]

    assert client.drive_export_requests == [('sheet-1', 'text/csv')]
    assert event.body == '항목,금액\n출장비,120000\n식대,45000'
    assert event.raw_metadata['parser_name'] == 'google_drive_sheets_csv_export'
    assert event.raw_metadata['parser_status'] == 'parsed'
    assert event.raw_metadata['parser_status_reason'] is None
    assert event.raw_metadata['document_version'] == '7'
    assert event.raw_metadata['revision_id'] == 'sheet-rev-7'
    assert event.raw_metadata['content_signature'] == 'drive:sheet-1:7:sheet-rev-7'
    assert event.raw_metadata['source_snippet'] == '항목,금액 출장비,120000 식대,45000'


@pytest.mark.parametrize(
    ('mime_type', 'expected_status', 'expected_reason'),
    [
        ('application/vnd.google-apps.presentation', 'metadata_only', 'slides_export_not_enabled'),
        ('application/pdf', 'metadata_only', 'pdf_parser_not_enabled'),
        (
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'metadata_only',
            'docx_parser_not_enabled',
        ),
        ('application/x-hwp', 'unsupported', 'hwp_parser_not_decided'),
        ('application/haansofthwp', 'unsupported', 'hwp_parser_not_decided'),
        ('application/vnd.hancom.hwpx', 'unsupported', 'hwp_parser_not_decided'),
    ],
)
def test_google_connector_marks_drive_parser_status_by_mime_type(
    mime_type: str,
    expected_status: str,
    expected_reason: str,
) -> None:
    client = FakeGoogleClient(
        drive_files=[
            {
                'id': 'file-typed',
                'name': '타입별 문서',
                'mimeType': mime_type,
                'webViewLink': 'https://drive.google.com/file/d/file-typed/view',
                'modifiedTime': '2026-05-01T09:00:00Z',
                'version': '42',
                'headRevisionId': 'rev-42',
                'owners': [{'emailAddress': 'owner@example.com'}],
            }
        ]
    )
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='drive',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    )

    event = connector.fetch_events()[0]

    assert client.drive_export_requests == []
    assert event.raw_metadata['parser_name'] == 'google_drive_metadata'
    assert event.raw_metadata['parser_status'] == expected_status
    assert event.raw_metadata['parser_status_reason'] == expected_reason
    assert event.raw_metadata['mime_type'] == mime_type
    assert event.raw_metadata['document_version'] == '42'
    assert event.raw_metadata['revision_id'] == 'rev-42'
    assert event.raw_metadata['content_signature'] == 'drive:file-typed:42:rev-42'
    assert 'Google Drive file changed: 타입별 문서' in event.body


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


def test_google_connector_fetches_calendar_events_since_latest_cursor() -> None:
    client = FakeGoogleClient()
    connector = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type='calendar',
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    )

    events = connector.fetch_events_since({'calendar': '2026-05-01T10:00:00Z'})

    assert len(events) == 1
    assert client.calendar_updated_min == '2026-05-01T10:00:00Z'


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
    assert event.body == (
        'PM 회의\n\nDescription: 런칭 일정 점검\nLocation: 회의실 A\n'
        'Start: 2026-05-02T09:00:00+09:00\nEnd: 2026-05-02T10:00:00+09:00'
    )
    assert event.author == 'pm@example.com'
    assert event.participants == ['pm@example.com', 'dev@example.com', 'client@customer.co.kr']
    assert event.timestamp == datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    assert event.raw_metadata['sync_partition'] == 'calendar'
    assert event.raw_metadata['sync_cursor'] == '2026-05-01T10:00:00Z'
    assert event.raw_metadata['location'] == '회의실 A'
    assert event.raw_metadata['attendee_count'] == 3
    assert event.raw_metadata['event_context_key'] == 'event-1:2026-05-01T10:00:00Z'
    assert event.raw_metadata['event_status'] == 'confirmed'
    assert event.raw_metadata['organizer_email'] == 'lead@example.com'
    assert event.raw_metadata['creator_email'] == 'pm@example.com'
    assert event.raw_metadata['recurring_event_id'] == 'series-1'
    assert event.raw_metadata['attendee_response_statuses'] == {
        'accepted': 1,
        'declined': 1,
        'needsAction': 1,
    }
    assert event.raw_metadata['attendee_domains'] == ['customer.co.kr', 'example.com']
    assert event.raw_metadata['external_domains'] == ['customer.co.kr']
    assert event.raw_metadata['has_external_attendees'] is True
    assert event.raw_metadata['duration_minutes'] == 60


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
    assert detail_request.url.params['format'] == 'full'


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
    assert 'description' in requests[0].url.params['fields']
    assert 'lastModifyingUser' in requests[0].url.params['fields']
    assert 'version' in requests[0].url.params['fields']
    assert 'headRevisionId' in requests[0].url.params['fields']
    assert requests[1].url.params['pageToken'] == 'drive-page-2'


def test_google_web_api_client_exports_drive_file_as_text() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text='휴가 신청은 HR 시스템에서 진행합니다.')

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    text = client.drive_file_text_export(file_id='file-1', export_mime_type='text/plain')

    assert text == '휴가 신청은 HR 시스템에서 진행합니다.'
    assert requests[0].url.path == '/drive/v3/files/file-1/export'
    assert requests[0].url.params['mimeType'] == 'text/plain'


def test_google_web_api_client_paginates_calendar_events() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.params.get('pageToken') is None:
            return httpx.Response(
                200,
                json={
                    'items': [{'id': 'event-1', 'summary': 'First'}],
                    'nextPageToken': 'calendar-page-2',
                },
            )
        return httpx.Response(200, json={'items': [{'id': 'event-2', 'summary': 'Second'}]})

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        page_limit=1,
    )

    events = client.calendar_events()

    assert [event['id'] for event in events] == ['event-1', 'event-2']
    assert requests[0].url.path == '/calendar/v3/calendars/primary/events'
    assert requests[1].url.params['pageToken'] == 'calendar-page-2'


def test_google_web_api_client_sends_delta_params_for_gmail_drive_and_calendar() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == '/gmail/v1/users/me/messages':
            return httpx.Response(200, json={'messages': []})
        if request.url.path == '/drive/v3/files':
            return httpx.Response(200, json={'files': []})
        if request.url.path == '/calendar/v3/calendars/primary/events':
            return httpx.Response(200, json={'items': []})
        raise AssertionError(f'unexpected request: {request.url}')

    client = GoogleWebApiClient(
        oauth_token='google-oauth-token',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.gmail_messages(after_internal_date='1777600800000') == []
    assert client.drive_files(modified_after='2026-05-01T09:00:00Z') == []
    assert client.calendar_events(updated_min='2026-05-01T10:00:00Z') == []

    gmail_request = next(request for request in requests if request.url.path == '/gmail/v1/users/me/messages')
    drive_request = next(request for request in requests if request.url.path == '/drive/v3/files')
    calendar_request = next(request for request in requests if request.url.path == '/calendar/v3/calendars/primary/events')
    assert gmail_request.url.params['q'] == 'after:1777600800'
    assert drive_request.url.params['q'] == "modifiedTime > '2026-05-01T09:00:00Z'"
    assert calendar_request.url.params['updatedMin'] == '2026-05-01T10:00:00Z'


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
