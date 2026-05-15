from agent_slack import agent_slack as agent_module
from agent_slack.agent_slack import SlackAgentState, classify_work_node
from agent_slack.project_routing import (
    ProjectOption,
    ProjectRoutingDecision,
    ProjectRoutingResult,
)
from backend.app.agent_runtime.contracts import ReviewCandidate


def test_agent_slack_work_filter_skips_low_signal_messages_before_llm(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError('low-signal messages should not call the LLM work filter')

    monkeypatch.setattr(agent_module, 'ChatOpenAI', fail_if_called)
    state = SlackAgentState(
        channel_id='C123',
        messages=[
            {'ts': '1777600800.000100', 'text': '후...'},
            {'ts': '1777600801.000100', 'text': '부탁드립니다.'},
        ],
        openai_api_key='test-key',
    )

    result = classify_work_node(state)

    assert result['is_work_related'] is False
    assert result['processed_text'] == ''


def test_agent_slack_applies_project_routing_to_candidates(monkeypatch) -> None:
    def fake_route_projects_for_candidates(*, model, projects, candidates):
        return ProjectRoutingResult(
            decisions=[
                ProjectRoutingDecision(
                    source_id='C123:1777600800.000100',
                    item_index=0,
                    project_key='project-alpha',
                    project_name='Project Alpha',
                    confidence_score=0.86,
                    assignment_summary='Redis 큐 상태와 동기화 안정성 개선 논의입니다.',
                    assignment_reason='Redis와 sync job 근거가 Project Alpha와 일치합니다.',
                )
            ],
            input_tokens=10,
            output_tokens=5,
            model_name='fake-project-router',
        )

    monkeypatch.setattr(
        agent_module,
        'route_projects_for_candidates',
        fake_route_projects_for_candidates,
    )
    state = SlackAgentState(
        channel_id='C123',
        candidates=[
            ReviewCandidate(
                item_type='history_event',
                title='Redis 큐 상태 확인',
                summary='Redis 큐와 동기화 작업 상태를 확인했습니다.',
                source_links=[
                    'https://example.slack.com/archives/C123/p1777600800000100'
                ],
                source_snippets=['Redis queue 상태를 확인하고 sync job을 복구합니다.'],
                confidence_score=0.91,
                permission_level='internal',
                payload_fields={'topic_tag': 'Redis'},
            )
        ],
        projects=[
            ProjectOption(
                project_key='project-alpha',
                name='Project Alpha',
                summary='Redis queue status and sync job reliability work',
            )
        ],
        project_router_model=object(),
    )

    result = agent_module.project_route_node(state)

    routed = result['candidates'][0]
    assert routed.payload_fields['project_key'] == 'project-alpha'
    assert routed.payload_fields['project_assignment_method'] == 'llm_tool'
    assert (
        routed.payload_fields['project_assignment_summary']
        == 'Redis 큐 상태와 동기화 안정성 개선 논의입니다.'
    )
    assert result['project_prompt_tokens'] == 10
    assert result['project_completion_tokens'] == 5


def test_agent_slack_routes_every_candidate_and_marks_unmatched_for_user_selection() -> None:
    class FakeProjectRouter:
        def invoke(self, payload):
            return {
                'model_name': 'fake-router',
                'input_tokens': 12,
                'output_tokens': 9,
                'decisions': [
                    {
                        'source_id': 'C123:candidate-0',
                        'item_index': 0,
                        'project_key': 'project-alpha',
                        'project_name': 'Project Alpha',
                        'confidence_score': 0.9,
                        'assignment_summary': 'Redis 큐 안정화 활동입니다.',
                        'assignment_reason': 'Redis와 sync job 단서가 Project Alpha와 일치합니다.',
                        'alternatives': [],
                        'needs_user_selection': False,
                    },
                    {
                        'source_id': 'C123:candidate-1',
                        'item_index': 1,
                        'project_key': None,
                        'project_name': None,
                        'confidence_score': 0.41,
                        'assignment_summary': '등록 프로젝트와 직접 일치하지 않습니다.',
                        'assignment_reason': '프로젝트 이름/설명과 매칭되는 근거가 부족합니다.',
                        'alternatives': ['Project Alpha'],
                        'needs_user_selection': True,
                    },
                ],
            }

    candidates = [
        ReviewCandidate(
            title='Redis 큐 점검',
            summary='Redis 큐 상태를 확인했습니다.',
            item_type='history_event',
            source_links=[],
            source_snippets=['Redis 큐 상태 확인'],
            confidence_score=0.86,
            permission_level='internal',
        ),
        ReviewCandidate(
            title='새 캠페인 킥오프',
            summary='아직 등록되지 않은 캠페인 논의입니다.',
            item_type='todo',
            source_links=[],
            source_snippets=['새 캠페인 준비 필요'],
            confidence_score=0.82,
            permission_level='internal',
        ),
    ]
    state = SlackAgentState(
        channel_id='C123',
        candidates=candidates,
        projects=[
            ProjectOption(
                project_key='project-alpha',
                name='Project Alpha',
                summary='Redis sync work',
            )
        ],
        project_router_model=FakeProjectRouter(),
    )

    result = agent_module.project_route_node(state)

    first, second = result['candidates']
    assert first.payload_fields['project_key'] == 'project-alpha'
    assert first.payload_fields['project_assignment_method'] == 'llm_tool'
    assert first.payload_fields['project_needs_user_selection'] is False
    assert 'project_key' not in second.payload_fields
    assert second.payload_fields['project_assignment_method'] == 'llm_tool'
    assert second.payload_fields['project_needs_user_selection'] is True
    assert (
        second.payload_fields['project_assignment_reason']
        == '프로젝트 이름/설명과 매칭되는 근거가 부족합니다.'
    )
