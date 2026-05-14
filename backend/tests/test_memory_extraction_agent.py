from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.memory_extraction_agent import (
    DecisionRecordAgent,
    DeterministicDecisionRecordModel,
    DeterministicHistoryModel,
    DeterministicTimelineModel,
    DeterministicTodoModel,
    HistoryAgent,
    TimelineAgent,
    TodoAgent,
    ValidationAgent,
)


def build_packet() -> EvidencePacket:
    return EvidencePacket(
        source_type='company_memory',
        source_window='test:track-c',
        messages=[
            EvidenceMessage(
                source_id='slack-1',
                source_url='https://slack.mock/1',
                text='결정: Redis를 작업 상태 공유에 사용하고 PostgreSQL은 영구 기록 저장소로 유지합니다.',
                author='sara@example.com',
                timestamp='2026-05-02T09:00:00+09:00',
                permission_level='internal',
            ),
            EvidenceMessage(
                source_id='gmail-1',
                source_url='https://gmail.mock/1',
                text='QA 완료 후 배포를 진행했습니다. 이유는 고객 데모 일정이 확정되었기 때문입니다.',
                author='owner@example.com',
                timestamp='2026-05-02T10:00:00+09:00',
                permission_level='internal',
            ),
            EvidenceMessage(
                source_id='slack-2',
                source_url='https://slack.mock/2',
                text='TODO: Slack OAuth redirect URI를 확인하고 런칭 전에 권한 테스트를 마칩니다.',
                author='dev@example.com',
                timestamp='2026-05-02T11:00:00+09:00',
                permission_level='internal',
            ),
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )


def test_track_c_extraction_agents_create_structured_review_candidates() -> None:
    packet = build_packet()

    timeline = TimelineAgent(model=DeterministicTimelineModel()).run(packet)
    history = HistoryAgent(model=DeterministicHistoryModel()).run(packet)
    decision = DecisionRecordAgent(model=DeterministicDecisionRecordModel()).run(packet)
    todo = TodoAgent(model=DeterministicTodoModel()).run(packet)

    assert timeline.agent_name == 'timeline_agent'
    assert timeline.candidates[0].item_type == 'timeline_event'
    assert timeline.candidates[0].payload_fields['result_summary']
    assert history.agent_name == 'history_agent'
    assert history.candidates[0].item_type == 'history_event'
    assert history.candidates[0].payload_fields['reason']
    assert decision.agent_name == 'decision_record_agent'
    assert decision.candidates[0].item_type == 'decision_record'
    assert 'Redis' in decision.candidates[0].payload_fields['decision_summary']
    assert todo.agent_name == 'todo_agent'
    assert todo.candidates[0].item_type == 'todo'
    assert todo.candidates[0].payload_fields['priority'] == 'high'


def test_validation_agent_requires_evidence_and_confidence_floor() -> None:
    packet = build_packet()
    candidate = DecisionRecordAgent(model=DeterministicDecisionRecordModel()).run(packet).candidates[0]
    validation = ValidationAgent(min_confidence=0.7)
    weak_candidate = candidate.__class__(
        item_type=candidate.item_type,
        title=candidate.title,
        summary=candidate.summary,
        source_links=candidate.source_links,
        source_snippets=candidate.source_snippets,
        confidence_score=0.3,
        permission_level=candidate.permission_level,
        uncertainty_reason=candidate.uncertainty_reason,
        payload_fields=candidate.payload_fields,
    )

    assert validation.accept(candidate) is True
    assert validation.accept(weak_candidate) is False


def test_deterministic_todo_model_extracts_assignee_and_due_date_from_drive_or_calendar_evidence() -> None:
    packet = EvidencePacket(
        source_type='company_memory',
        source_window='test:drive-calendar-assignment',
        messages=[
            EvidenceMessage(
                source_id='drive-plan-1',
                source_url='https://drive.mock/project-alpha/plan',
                text='담당: 김하나\n업무: 고객사 공유본 준비\n기한: 2026-05-20',
                author='owner@example.com',
                timestamp='2026-05-13T09:00:00+09:00',
                permission_level='restricted',
                metadata={'source_type': 'drive'},
                source_snippet_override='담당: 김하나 업무: 고객사 공유본 준비 기한: 2026-05-20',
            ),
            EvidenceMessage(
                source_id='calendar-deadline-1',
                source_url='https://calendar.mock/project-alpha/deadline',
                text='고객사 공유본 준비 마감',
                author='lead@example.com',
                timestamp='2026-05-20T09:00:00+09:00',
                permission_level='internal',
                metadata={'source_type': 'calendar', 'start': '2026-05-20T09:00:00+09:00'},
            ),
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )

    todo = TodoAgent(model=DeterministicTodoModel()).run(packet).candidates[0]

    assert todo.item_type == 'todo'
    assert todo.permission_level == 'restricted'
    assert todo.payload_fields['assignee'] == '김하나'
    assert todo.payload_fields['due_date'] == '2026-05-20'
    assert todo.payload_fields['task_summary'] == '고객사 공유본 준비'
    assert todo.payload_fields['evidence_reason']
