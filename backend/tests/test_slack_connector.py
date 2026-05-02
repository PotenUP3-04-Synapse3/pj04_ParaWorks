from datetime import UTC, datetime

import httpx
import pytest

from backend.app.connectors.slack import (
    SLACK_REQUIRED_HISTORY_SCOPES,
    SlackApiError,
    SlackConnector,
    SlackConnectorConfig,
    SlackWebApiClient,
)


class FakeSlackClient:
    def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
        assert channel_id == 'C123'
        assert oldest is None
        return [
            {
                'type': 'message',
                'user': 'U123',
                'text': 'Redis 결정을 검토 큐와 연결해주세요.',
                'ts': '1777600800.000100',
            }
        ]


def test_slack_required_history_scopes_cover_channel_types() -> None:
    assert SLACK_REQUIRED_HISTORY_SCOPES == (
        'channels:history',
        'groups:history',
        'im:history',
        'mpim:history',
    )


def test_slack_connector_maps_history_messages_to_source_events() -> None:
    connector = SlackConnector(
        config=SlackConnectorConfig(
            bot_token='xoxb-test',
            channel_ids=['C123'],
            workspace_url='https://example.slack.com',
        ),
        client=FakeSlackClient(),
    )

    events = connector.fetch_events()

    assert len(events) == 1
    event = events[0]
    assert event.source_type == 'slack'
    assert event.source_id == 'C123:1777600800.000100'
    assert event.source_url == 'https://example.slack.com/archives/C123/p1777600800000100'
    assert event.title == 'Slack message in C123'
    assert event.body == 'Redis 결정을 검토 큐와 연결해주세요.'
    assert event.author == 'U123'
    assert event.participants == ['U123']
    assert event.timestamp == datetime.fromtimestamp(1777600800.000100, tz=UTC)
    assert event.permission_level == 'internal'
    assert event.raw_metadata['required_scopes'] == list(SLACK_REQUIRED_HISTORY_SCOPES)


def test_slack_connector_fetches_incremental_history_after_channel_cursor() -> None:
    observed_oldest: list[str | None] = []

    class IncrementalFakeSlackClient:
        def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
            assert channel_id == 'C123'
            observed_oldest.append(oldest)
            return [
                {
                    'type': 'message',
                    'user': 'U456',
                    'text': 'newer decision',
                    'ts': '1777600900.000100',
                }
            ]

    connector = SlackConnector(
        config=SlackConnectorConfig(
            bot_token='xoxb-test',
            channel_ids=['C123'],
            workspace_url='https://example.slack.com',
        ),
        client=IncrementalFakeSlackClient(),
    )

    events = connector.fetch_events_since({'C123': '1777600800.000100'})

    assert observed_oldest == ['1777600800.000100']
    assert [event.source_id for event in events] == ['C123:1777600900.000100']


def test_slack_web_api_client_fetches_paginated_history_with_bearer_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers['authorization'] == 'Bearer xoxb-test'
        cursor = request.url.params.get('cursor')
        if cursor:
            return httpx.Response(
                200,
                json={
                    'ok': True,
                    'messages': [
                        {'type': 'message', 'user': 'U2', 'text': 'second page', 'ts': '2.000100'}
                    ],
                    'response_metadata': {},
                },
            )
        return httpx.Response(
            200,
            json={
                'ok': True,
                'messages': [
                    {'type': 'message', 'user': 'U1', 'text': 'first page', 'ts': '1.000100'}
                ],
                'response_metadata': {'next_cursor': 'cursor-2'},
            },
        )

    client = SlackWebApiClient(
        bot_token='xoxb-test',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    messages = client.conversation_history('C123')

    assert [message['text'] for message in messages] == ['first page', 'second page']
    assert requests[0].url.path == '/api/conversations.history'
    assert requests[0].url.params['channel'] == 'C123'
    assert requests[0].url.params['limit'] == '200'
    assert requests[1].url.params['cursor'] == 'cursor-2'


def test_slack_web_api_client_sends_oldest_for_incremental_history() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                'ok': True,
                'messages': [{'type': 'message', 'user': 'U1', 'text': 'new page', 'ts': '2.000100'}],
                'response_metadata': {},
            },
        )

    client = SlackWebApiClient(
        bot_token='xoxb-test',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    client.conversation_history('C123', oldest='1.000100')

    assert requests[0].url.params['oldest'] == '1.000100'


def test_slack_web_api_client_retries_rate_limited_history_with_retry_after() -> None:
    requests: list[httpx.Request] = []
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={'Retry-After': '2'})
        return httpx.Response(
            200,
            json={
                'ok': True,
                'messages': [{'type': 'message', 'user': 'U1', 'text': 'after retry', 'ts': '2.000100'}],
                'response_metadata': {},
            },
        )

    client = SlackWebApiClient(
        bot_token='xoxb-test',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleep_calls.append,
    )

    messages = client.conversation_history('C123')

    assert [message['text'] for message in messages] == ['after retry']
    assert len(requests) == 2
    assert sleep_calls == [2.0]


def test_slack_web_api_client_stops_retrying_rate_limited_history_after_limit() -> None:
    requests: list[httpx.Request] = []
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(429, headers={'Retry-After': '1'})

    client = SlackWebApiClient(
        bot_token='xoxb-test',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=1,
        sleep=sleep_calls.append,
    )

    with pytest.raises(SlackApiError, match='rate_limited'):
        client.conversation_history('C123')

    assert len(requests) == 2
    assert sleep_calls == [1.0]


def test_slack_web_api_client_retries_transient_server_history_errors() -> None:
    requests: list[httpx.Request] = []
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                'ok': True,
                'messages': [{'type': 'message', 'user': 'U1', 'text': 'server recovered', 'ts': '3.000100'}],
                'response_metadata': {},
            },
        )

    client = SlackWebApiClient(
        bot_token='xoxb-test',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleep_calls.append,
    )

    messages = client.conversation_history('C123')

    assert [message['text'] for message in messages] == ['server recovered']
    assert len(requests) == 2
    assert sleep_calls == [1.0]


def test_slack_web_api_client_raises_clear_error_for_slack_api_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'ok': False, 'error': 'missing_scope'})

    client = SlackWebApiClient(
        bot_token='xoxb-test',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(SlackApiError, match='missing_scope'):
        client.conversation_history('C123')
