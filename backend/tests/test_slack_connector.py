from datetime import UTC, datetime

from backend.app.connectors.slack import (
    SLACK_REQUIRED_HISTORY_SCOPES,
    SlackConnector,
    SlackConnectorConfig,
)


class FakeSlackClient:
    def conversation_history(self, channel_id: str) -> list[dict]:
        assert channel_id == 'C123'
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
