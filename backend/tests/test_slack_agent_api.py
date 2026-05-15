from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import AgentRunCost, ReviewCandidate, TokenUsage
from backend.app.agents.slack_agent import sync_service
from backend.app.connectors.mock import get_mock_connector
from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.models import AgentRun, Project, ReviewItem


def test_slack_agent_review_endpoint_creates_agent_review_item(client, db_session: Session) -> None:
    sync_response = client.post('/api/v1/integrations/slack/sync')
    assert sync_response.status_code == 200

    response = client.post('/api/v1/integrations/slack/agent-review')

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        'agent_name': 'slack_agent',
        'status': 'complete',
        'created_review_items': 1,
    }

    agent_item = db_session.scalar(
        select(ReviewItem).where(ReviewItem.payload['agent_name'].as_string() == 'slack_agent')
    )
    assert agent_item is not None
    assert agent_item.status == 'pending_review'
    assert agent_item.payload['prompt_version'] == 'slack-timeline:v1'
    assert agent_item.payload['token_usage']['total_tokens'] > 0
    assert agent_item.payload['estimated_cost_usd'] > 0
    assert agent_item.source_links
    assert agent_item.source_snippets


def test_slack_sync_uses_agent_slack_llm_pipeline_when_provider_key_exists(
    client,
    db_session: Session,
    monkeypatch,
) -> None:
    def override_settings() -> Settings:
        return Settings(paraworks_demo_mode=False, openai_api_key='openai-key')

    observed: list[dict[str, object]] = []

    def fake_process_daily_slack_sync(
        channel_id: str,
        messages: list[dict],
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
        projects: list[dict[str, str]] | None = None,
        project_router_model=None,
    ) -> dict:
        observed.append(
            {
                'channel_id': channel_id,
                'message_count': len(messages),
                'openai_api_key': openai_api_key,
                'project_count': len(projects or []),
            }
        )
        return {
            'model_name': 'gpt-4o-mini',
            'is_work_related': True,
            'run_cost': AgentRunCost(
                model_name='gpt-4o-mini',
                token_usage=TokenUsage(input_tokens=120, output_tokens=40),
                estimated_cost_usd=0.000042,
                cache_hit=False,
            ),
            'candidates': [
                ReviewCandidate(
                    item_type='decision_record',
                    title='Slack LLM 결정사항',
                    summary='agent_slack LLM 파이프라인이 동기화된 Slack 근거에서 결정사항을 추출했다.',
                    source_links=[f'https://example.slack.com/archives/{channel_id}/p1777600800000100'],
                    source_snippets=['Redis 진행 상태를 Slack 근거로 확인했다.'],
                    confidence_score=0.91,
                    permission_level='internal',
                    payload_fields={
                        'category': 'Project',
                        'topic_tag': 'Redis',
                        'importance': 'High',
                    },
                )
            ],
        }

    client.app.dependency_overrides[get_settings] = override_settings
    client.app.dependency_overrides[get_demo_user] = lambda: DemoUser(
        id='demo-admin',
        email='admin@paraworks.local',
        role='admin',
        permission_levels={'public', 'internal', 'restricted'},
        name='관리자',
        title='관리자',
        department='Platform',
    )
    monkeypatch.setattr(
        'backend.app.api.v1.integrations.get_sync_connector',
        lambda *args, **kwargs: get_mock_connector('slack'),
    )
    monkeypatch.setattr(sync_service, 'process_daily_slack_sync', fake_process_daily_slack_sync)

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert response.json()['created_review_items'] == len(observed)
    assert sum(item['message_count'] for item in observed) == len(response.json()['changed_source_ids'])
    assert {item['openai_api_key'] for item in observed} == {'openai-key'}

    agent_runs = db_session.scalars(select(AgentRun).where(AgentRun.agent_name == 'slack_agent_v2')).all()
    assert len(agent_runs) == len(observed)
    assert {agent_run.model_name for agent_run in agent_runs} == {'gpt-4o-mini'}
    assert {agent_run.source_window for agent_run in agent_runs} == {
        f"slack:{item['channel_id']}" for item in observed
    }

    review_items = db_session.scalars(select(ReviewItem)).all()
    assert len(review_items) == len(observed)
    assert {review_item.payload['title'] for review_item in review_items} == {'Slack LLM 결정사항'}
    assert {review_item.payload['prompt_version'] for review_item in review_items} == {'slack-taxonomy:v3'}
    assert all(review_item.payload['source_ids'] for review_item in review_items)


def test_slack_agent_project_routing_metadata_is_persisted(
    client,
    db_session: Session,
    monkeypatch,
) -> None:
    def override_settings() -> Settings:
        return Settings(paraworks_demo_mode=False, openai_api_key='openai-key')

    observed_projects: list[list[dict[str, str]]] = []

    def fake_process_daily_slack_sync(
        channel_id: str,
        messages: list[dict],
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
        projects: list[dict[str, str]] | None = None,
        project_router_model=None,
    ) -> dict:
        observed_projects.append(projects or [])
        return {
            'model_name': 'gpt-5-mini',
            'is_work_related': True,
            'project_model_name': 'fake-project-router',
            'project_prompt_tokens': 12,
            'project_completion_tokens': 6,
            'run_cost': AgentRunCost(
                model_name='gpt-5-mini',
                token_usage=TokenUsage(input_tokens=120, output_tokens=40),
                estimated_cost_usd=0.000042,
                cache_hit=False,
            ),
            'candidates': [
                ReviewCandidate(
                    item_type='history_event',
                    title='Redis 큐 상태 확인',
                    summary='Redis 큐와 동기화 작업 상태를 확인했습니다.',
                    source_links=[
                        f'https://example.slack.com/archives/{channel_id}/p1777600800000100'
                    ],
                    source_snippets=[
                        'Redis queue 상태를 확인하고 sync job을 복구합니다.'
                    ],
                    confidence_score=0.91,
                    permission_level='internal',
                    payload_fields={
                        'category': 'Project',
                        'topic_tag': 'Redis',
                        'importance': 'High',
                        'project_key': 'project-alpha',
                        'project_name': 'Project Alpha',
                        'project_assignment_method': 'llm_tool',
                        'project_assignment_summary': (
                            'Redis 큐 상태와 동기화 안정성 개선 논의입니다.'
                        ),
                        'project_assignment_reason': (
                            'Redis와 sync job 근거가 Project Alpha와 일치합니다.'
                        ),
                        'project_assignment_confidence': 0.86,
                        'project_alternatives': [],
                        'project_needs_user_selection': False,
                    },
                )
            ],
        }

    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        )
    )
    db_session.commit()

    client.app.dependency_overrides[get_settings] = override_settings
    client.app.dependency_overrides[get_demo_user] = lambda: DemoUser(
        id='demo-admin',
        email='admin@paraworks.local',
        role='admin',
        permission_levels={'public', 'internal', 'restricted'},
        name='관리자',
        title='관리자',
        department='Platform',
    )
    monkeypatch.setattr(
        'backend.app.api.v1.integrations.get_sync_connector',
        lambda *args, **kwargs: get_mock_connector('slack'),
    )
    monkeypatch.setattr(sync_service, 'process_daily_slack_sync', fake_process_daily_slack_sync)

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert observed_projects
    assert observed_projects[0][0]['project_key'] == 'project-alpha'

    review_item = db_session.scalar(
        select(ReviewItem).where(ReviewItem.payload['agent_name'].as_string() == 'slack_agent')
    )
    assert review_item is not None
    assert review_item.payload['project_key'] == 'project-alpha'
    assert review_item.payload['project_name'] == 'Project Alpha'
    assert review_item.payload['project_assignment_method'] == 'llm_tool'
    assert (
        review_item.payload['project_assignment_summary']
        == 'Redis 큐 상태와 동기화 안정성 개선 논의입니다.'
    )
    assert (
        review_item.payload['project_assignment_reason']
        == 'Redis와 sync job 근거가 Project Alpha와 일치합니다.'
    )
    agent_run = db_session.scalar(select(AgentRun).where(AgentRun.agent_name == 'slack_agent_v2'))
    assert agent_run is not None
    assert agent_run.metadata_['project_routing'] == {
        'enabled': True,
        'method': 'langchain_tools',
        'project_count': 1,
        'model_name': 'fake-project-router',
        'input_tokens': 12,
        'output_tokens': 6,
    }


def test_slack_agent_review_item_uses_only_tool_project_routing(
    monkeypatch,
    client,
    db_session,
) -> None:
    db_session.add(Project(project_key='project-alpha', name='Project Alpha', summary='Redis work'))
    db_session.commit()

    def override_settings() -> Settings:
        return Settings(paraworks_demo_mode=False, openai_api_key='openai-key')

    def fake_process_daily_slack_sync(*args, **kwargs):
        return {
            'is_work_related': True,
            'model_name': 'gpt-5-mini',
            'project_model_name': 'fake-router',
            'project_prompt_tokens': 10,
            'project_completion_tokens': 5,
            'run_cost': AgentRunCost(
                model_name='gpt-5-mini',
                token_usage=TokenUsage(input_tokens=100, output_tokens=50),
                estimated_cost_usd=0.0001,
                cache_hit=False,
            ),
            'candidates': [
                ReviewCandidate(
                    title='등록 프로젝트 없음',
                    summary='topic_tag에는 Project Alpha가 있어도 router가 매칭하지 않았습니다.',
                    item_type='history_event',
                    source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
                    source_snippets=['새 프로젝트 후보입니다.'],
                    confidence_score=0.8,
                    permission_level='internal',
                    payload_fields={
                        'topic_tag': 'Project Alpha',
                        'project_assignment_method': 'llm_tool',
                        'project_assignment_summary': '등록 프로젝트와 확정 매칭되지 않습니다.',
                        'project_assignment_reason': 'router가 사용자 선택 필요로 판단했습니다.',
                        'project_assignment_confidence': 0.41,
                        'project_needs_user_selection': True,
                    },
                ),
            ],
        }

    client.app.dependency_overrides[get_settings] = override_settings
    client.app.dependency_overrides[get_demo_user] = lambda: DemoUser(
        id='demo-admin',
        email='admin@paraworks.local',
        role='admin',
        permission_levels={'public', 'internal', 'restricted'},
        name='관리자',
        title='관리자',
        department='Platform',
    )
    monkeypatch.setattr(
        'backend.app.api.v1.integrations.get_sync_connector',
        lambda *args, **kwargs: get_mock_connector('slack'),
    )
    monkeypatch.setattr(sync_service, 'process_daily_slack_sync', fake_process_daily_slack_sync)

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    item = db_session.scalar(
        select(ReviewItem)
        .where(ReviewItem.item_type == 'history_event')
        .where(ReviewItem.payload['title'].as_string() == '등록 프로젝트 없음')
        .limit(1)
    )
    assert item is not None
    assert item.payload['project_assignment_method'] == 'llm_tool'
    assert item.payload['project_needs_user_selection'] is True
    assert item.payload.get('project_key') in (None, '')


def test_slack_llm_preflight_requires_explicit_enablement(client) -> None:
    def override_settings() -> Settings:
        return Settings(agent_llm_enabled=False)

    client.app.dependency_overrides[get_settings] = override_settings
    client.post('/api/v1/integrations/slack/sync')

    response = client.get('/api/v1/integrations/slack/agent-review/llm/preflight')

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'blocked'
    assert payload['reason'] == 'llm_disabled'
    assert payload['source_window'] == 'slack:live:ranked:12'
    assert payload['requires_paid_confirmation'] is True


def test_slack_llm_agent_review_requires_paid_confirmation(client) -> None:
    def override_settings() -> Settings:
        return Settings(
            agent_llm_enabled=True,
            openai_api_key='openai-key',
            gemini_api_key='gemini-key',
            agent_llm_max_estimated_cost_usd=1.0,
        )

    client.app.dependency_overrides[get_settings] = override_settings
    client.post('/api/v1/integrations/slack/sync')

    response = client.post('/api/v1/integrations/slack/agent-review/llm', json={'confirm_paid_run': False})

    assert response.status_code == 400
    assert response.json()['detail'] == 'Paid LLM run requires confirm_paid_run=true'


def test_slack_llm_preflight_exposes_azure_openai_alias_with_openai_key(client) -> None:
    def override_settings() -> Settings:
        return Settings(
            agent_llm_enabled=True,
            agent_llm_provider_order='azure_openai,openai,gemini',
            openai_api_key='openai-compatible-key',
            gemini_api_key=None,
            google_api_key=None,
            agent_llm_max_estimated_cost_usd=1.0,
        )

    client.app.dependency_overrides[get_settings] = override_settings
    client.post('/api/v1/integrations/slack/sync')

    response = client.get('/api/v1/integrations/slack/agent-review/llm/preflight')

    assert response.status_code == 200
    payload = response.json()
    assert payload['provider_order'] == ['azure_openai', 'openai', 'gemini']
    assert payload['available_providers'] == ['azure_openai', 'openai']
    assert payload['action'] == 'run'
