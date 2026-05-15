from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.agent_runtime import PermissionContext
from backend.app.agents.slack_agent.quality import classify_slack_work_signal
from backend.app.agents.slack_agent.service import build_slack_evidence_packet
from backend.app.connectors.base import SourceEvent
from backend.app.ingestion.service import ingest_events


def _slack_event(source_id: str, body: str) -> SourceEvent:
    return SourceEvent(
        source_type='slack',
        source_id=source_id,
        source_url=f'https://slack.mock/archives/C123/p{source_id[-16:]}',
        title='Slack message in C123',
        body=body,
        author='owner@example.com',
        participants=['owner@example.com'],
        timestamp=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        permission_level='internal',
        raw_metadata={
            'channel_id': 'C123',
            'ts': source_id.split(':')[-1],
            'sync_cursor': '2026-05-01T09:00:00Z',
        },
    )


def test_slack_work_signal_rejects_contextless_polite_requests() -> None:
    signal = classify_slack_work_signal('부탁드립니다.')

    assert signal.is_reviewable is False
    assert signal.reason == 'low_context_request'


def test_slack_work_signal_accepts_action_with_object_and_due_date() -> None:
    signal = classify_slack_work_signal('금요일까지 정산 파일 검토 부탁드립니다.')

    assert signal.is_reviewable is True
    assert 'work_object' in signal.reasons
    assert 'work_action' in signal.reasons
    assert 'due_context' in signal.reasons


def test_ranked_slack_packet_excludes_low_signal_messages(db_session: Session) -> None:
    ingest_events(
        db_session,
        [
            _slack_event('C123:1777600800.000100', '후...'),
            _slack_event('C123:1777600801.000100', '부탁드립니다.'),
            _slack_event('C123:1777600802.000100', '금요일까지 정산 파일 검토 부탁드립니다.'),
        ],
    )

    packet = build_slack_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='slack:test',
        selection_strategy='ranked',
    )

    assert [message.text for message in packet.messages] == ['금요일까지 정산 파일 검토 부탁드립니다.']
