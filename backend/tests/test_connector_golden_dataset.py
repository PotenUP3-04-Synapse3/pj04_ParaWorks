import json
from pathlib import Path

from backend.app.connectors.google import GoogleConnector, GoogleConnectorConfig
from backend.app.connectors.slack import SlackConnector, SlackConnectorConfig

FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'connector_golden_payloads.json'


class GoldenSlackClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
        assert channel_id == self.payload['channel_id']
        return list(self.payload['history'])

    def conversation_replies(
        self,
        channel_id: str,
        thread_ts: str,
        *,
        oldest: str | None = None,
    ) -> list[dict]:
        assert channel_id == self.payload['channel_id']
        assert thread_ts == self.payload['history'][0]['thread_ts']
        return list(self.payload['replies'])


class GoldenGoogleClient:
    def __init__(self, payloads: dict) -> None:
        self.payloads = payloads

    def gmail_messages(self, *, after_internal_date: str | None = None) -> list[dict]:
        return [self.payloads['gmail']]

    def drive_files(self, *, modified_after: str | None = None) -> list[dict]:
        return [self.payloads['drive']]

    def calendar_events(self, *, updated_min: str | None = None) -> list[dict]:
        return [self.payloads['calendar']]


def load_golden_payloads() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))


def test_connector_golden_dataset_preserves_agent_ready_metadata() -> None:
    payloads = load_golden_payloads()

    slack_events = SlackConnector(
        config=SlackConnectorConfig(
            bot_token='xoxb-test',
            channel_ids=[payloads['slack']['channel_id']],
            workspace_url=payloads['slack']['workspace_url'],
        ),
        client=GoldenSlackClient(payloads['slack']),
    ).fetch_events()
    google_client = GoldenGoogleClient(payloads)
    gmail_event = _google_event('gmail', google_client)
    drive_event = _google_event('drive', google_client)
    calendar_event = _google_event('calendar', google_client)

    assert len(slack_events) == 2
    slack_reply = slack_events[1]
    assert slack_reply.raw_metadata['thread_context_window'] == 'parent_plus_reply'
    assert slack_reply.raw_metadata['thread_parent_text'] == 'Decision: use pgvector for company memory search.'
    assert slack_reply.raw_metadata['thread_reply_index'] == 1

    assert gmail_event.raw_metadata['thread_context_key'] == 'thread-golden-1:msg-golden-1'
    assert gmail_event.raw_metadata['external_domains'] == ['client.co.kr']
    assert gmail_event.raw_metadata['has_external_participants'] is True

    assert drive_event.raw_metadata['parser_status'] == 'metadata_only'
    assert drive_event.raw_metadata['document_version'] == '42'
    assert drive_event.raw_metadata['content_signature'] == 'drive:file-golden-1:42:rev-42'

    assert calendar_event.raw_metadata['event_context_key'] == 'event-golden-1:2026-05-01T10:00:00Z'
    assert calendar_event.raw_metadata['attendee_response_statuses'] == {
        'accepted': 1,
        'declined': 1,
        'needsAction': 1,
    }
    assert calendar_event.raw_metadata['external_domains'] == ['customer.co.kr']
    assert calendar_event.raw_metadata['duration_minutes'] == 60


def _google_event(connector_type: str, client: GoldenGoogleClient):
    events = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type=connector_type,
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    ).fetch_events()
    assert len(events) == 1
    event = events[0]
    assert event.raw_metadata['required_scopes']
    assert event.source_url
    assert event.body
    return event
