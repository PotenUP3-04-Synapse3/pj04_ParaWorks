from backend.app.models import AgentRun


def test_agent_runs_api_returns_recent_runs_and_totals(client, db_session) -> None:
    first_run = AgentRun(
        agent_name='slack_agent',
        prompt_version='slack-timeline:v1',
        status='complete',
        source_window='mock-slack:all',
        cache_key='slack-cache-key',
        model_name='fake-slack-agent-model',
        input_tokens=700,
        output_tokens=140,
        total_tokens=840,
        estimated_cost_usd=0.000189,
        permission_level='internal',
        metadata_={'source_type': 'slack'},
    )
    second_run = AgentRun(
        agent_name='mail_document_agent',
        prompt_version='mail-document-history:v1',
        status='complete',
        source_window='mock-mail-docs:all',
        cache_key='mail-docs-cache-key',
        model_name='fake-mail-document-agent-model',
        input_tokens=1000,
        output_tokens=180,
        total_tokens=1180,
        estimated_cost_usd=0.000258,
        permission_level='restricted',
        metadata_={'included_source_types': ['drive', 'gmail']},
    )
    db_session.add_all([first_run, second_run])
    db_session.commit()

    response = client.get('/api/v1/agent-runs')

    assert response.status_code == 200
    payload = response.json()
    assert payload['total_runs'] == 2
    assert payload['total_tokens'] == 2020
    assert payload['estimated_cost_usd'] == 0.000447
    assert [run['agent_name'] for run in payload['recent_runs']] == [
        'mail_document_agent',
        'slack_agent',
    ]
    assert payload['recent_runs'][0]['prompt_version'] == 'mail-document-history:v1'
    assert payload['recent_runs'][0]['permission_level'] == 'restricted'
    assert payload['recent_runs'][0]['metadata']['included_source_types'] == ['drive', 'gmail']


def test_agent_run_detail_api_returns_single_run(client, db_session) -> None:
    agent_run = AgentRun(
        agent_name='rag_orchestrator_agent',
        prompt_version='rag-answer:v1',
        status='complete',
        source_window='ask:Redis queues',
        cache_key='rag-cache-key',
        model_name='fake-rag-orchestrator-model',
        input_tokens=80,
        output_tokens=32,
        total_tokens=112,
        estimated_cost_usd=0.000031,
        permission_level='internal',
        metadata_={'question': 'Redis queues', 'source_count': 2},
    )
    db_session.add(agent_run)
    db_session.commit()
    db_session.refresh(agent_run)

    response = client.get(f'/api/v1/agent-runs/{agent_run.id}')

    assert response.status_code == 200
    payload = response.json()
    assert payload['id'] == agent_run.id
    assert payload['agent_name'] == 'rag_orchestrator_agent'
    assert payload['prompt_version'] == 'rag-answer:v1'
    assert payload['cache_key'] == 'rag-cache-key'
    assert payload['token_usage'] == {
        'input_tokens': 80,
        'output_tokens': 32,
        'total_tokens': 112,
    }
    assert payload['metadata']['question'] == 'Redis queues'
    assert payload['estimated_cost_usd'] == 0.000031


def test_agent_run_detail_api_returns_404_for_missing_run(client) -> None:
    response = client.get('/api/v1/agent-runs/404')

    assert response.status_code == 404
    assert response.json()['detail'] == 'Agent run not found'
