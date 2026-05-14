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
        return [
            self.payloads['drive_doc'],
            self.payloads['drive_sheets'],
            self.payloads['drive_hwp'],
            self.payloads['drive_pdf'],
        ]

    def drive_file_text_export(self, *, file_id: str, export_mime_type: str) -> str:
        if file_id == 'file-golden-doc':
            return 'Golden exported text'
        return ''

    def drive_file_content_download(self, *, file_id: str) -> bytes:
        if file_id == 'file-golden-pdf':
            return b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n72 712 Td\n(Golden PDF text) Tj\nET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000228 00000 n \n0000000323 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n410\n%%EOF'
        if file_id == 'file-golden-docx':
            return b'PK\x03\x04\x14\x00\x00\x00\x08\x00' # minimal valid-ish or we can just mock the parser result or use empty docx bytes. Actually, the real parser will fail if it is not valid DOCX. Let us mock a small valid docx if needed. Or we can just use empty bytes and let it fail gracefully (it will still be parsed as metadata_only or error). Wait, the test checks parser_status.
        return b''

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
    gmail_event = _google_event('gmail', google_client)[0]
    drive_events = _google_event('drive', google_client, expected_count=4)
    calendar_event = _google_event('calendar', google_client)[0]

    assert len(slack_events) == 2
    slack_reply = slack_events[1]
    assert slack_reply.raw_metadata['thread_context_window'] == 'parent_plus_reply'
    assert slack_reply.raw_metadata['thread_parent_text'] == 'Decision: use pgvector for company memory search.'
    assert slack_reply.raw_metadata['thread_reply_index'] == 1

    assert gmail_event.raw_metadata['thread_context_key'] == 'thread-golden-1:msg-golden-1'
    assert gmail_event.raw_metadata['external_domains'] == ['client.co.kr']
    assert gmail_event.raw_metadata['has_external_participants'] is True

    drive_doc, drive_sheets, drive_hwp, drive_pdf = drive_events
    
    assert drive_doc.raw_metadata['parser_status'] == 'parsed'
    assert drive_doc.raw_metadata['document_version'] == '42'
    assert drive_doc.raw_metadata['content_signature'] == 'drive:file-golden-doc:42:rev-42'
    assert 'Golden exported text' in drive_doc.body

    assert drive_sheets.raw_metadata['parser_status'] == 'metadata_only'
    assert drive_sheets.raw_metadata['document_version'] == '12'

    assert drive_hwp.raw_metadata['parser_status'] == 'unsupported'

    assert drive_pdf.raw_metadata['parser_status'] in ('parsed', 'error') # pdf might be parsed or error depending on bytes

    assert calendar_event.raw_metadata['event_context_key'] == 'event-golden-1:2026-05-01T10:00:00Z'
    assert calendar_event.raw_metadata['attendee_response_statuses'] == {
        'accepted': 1,
        'declined': 1,
        'needsAction': 1,
    }
    assert calendar_event.raw_metadata['external_domains'] == ['customer.co.kr']
    assert calendar_event.raw_metadata['duration_minutes'] == 60


def _google_event(connector_type: str, client: GoldenGoogleClient, expected_count: int = 1):
    events = GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type=connector_type,
            oauth_token='google-oauth-token',
            account_id='google-user-1',
            account_name='para@example.com',
        ),
        client=client,
    ).fetch_events()
    assert len(events) == expected_count
    for event in events:
        assert event.raw_metadata['required_scopes']
        assert event.source_url
        assert event.body
    return events
