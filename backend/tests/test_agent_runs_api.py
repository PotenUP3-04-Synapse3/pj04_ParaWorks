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


def test_agent_run_detail_api_promotes_evidence_summary(client, db_session) -> None:
    agent_run = AgentRun(
        agent_name='slack_agent',
        prompt_version='slack-timeline:v1',
        status='complete',
        source_window='slack:live:ranked:12',
        cache_key='slack-cache-key',
        model_name='gpt-5.4-mini',
        input_tokens=2400,
        output_tokens=125,
        total_tokens=2525,
        estimated_cost_usd=0.000435,
        permission_level='internal',
        metadata_={
            'source_type': 'slack',
            'selection_strategy': 'ranked',
            'evidence_summary': [
                {
                    'rank': 1,
                    'source_id': 'C123:1.000100',
                    'source_url': 'https://example.slack.com/archives/C123/p1000100',
                    'timestamp': '1.000100',
                    'importance_score': 80,
                    'snippet': '결정: pgvector를 사용합니다.',
                }
            ],
        },
    )
    db_session.add(agent_run)
    db_session.commit()
    db_session.refresh(agent_run)

    response = client.get(f'/api/v1/agent-runs/{agent_run.id}')

    assert response.status_code == 200
    payload = response.json()
    assert payload['selection_strategy'] == 'ranked'
    assert payload['evidence_summary'][0]['rank'] == 1
    assert payload['evidence_summary'][0]['importance_score'] == 80


def test_agent_run_detail_api_returns_404_for_missing_run(client) -> None:
    response = client.get('/api/v1/agent-runs/404')

    assert response.status_code == 404
    assert response.json()['detail'] == 'Agent run not found'


def test_agent_run_summary_api_returns_cost_and_agent_breakdown(client, db_session) -> None:
    slack_first = AgentRun(
        agent_name='slack_agent',
        prompt_version='slack-timeline:v1',
        status='complete',
        source_window='mock-slack:all',
        cache_key='slack-cache-key-1',
        model_name='fake-slack-agent-model',
        input_tokens=500,
        output_tokens=100,
        total_tokens=600,
        estimated_cost_usd=0.00012,
        permission_level='internal',
        metadata_={'source_type': 'slack', 'cache_hit': False},
    )
    mail_failed = AgentRun(
        agent_name='mail_document_agent',
        prompt_version='mail-document-history:v1',
        status='failed',
        source_window='mock-mail-docs:all',
        cache_key='mail-docs-cache-key',
        model_name='fake-mail-document-agent-model',
        input_tokens=300,
        output_tokens=80,
        total_tokens=380,
        estimated_cost_usd=0.00009,
        permission_level='restricted',
        metadata_={'included_source_types': ['drive', 'gmail'], 'cache_hit': True},
    )
    slack_latest = AgentRun(
        agent_name='slack_agent',
        prompt_version='slack-timeline:v1',
        status='complete',
        source_window='mock-slack:channel:C-team',
        cache_key='slack-cache-key-2',
        model_name='fake-slack-agent-model',
        input_tokens=700,
        output_tokens=120,
        total_tokens=820,
        estimated_cost_usd=0.00017,
        permission_level='internal',
        metadata_={'source_type': 'slack', 'cache_hit': True},
    )
    db_session.add_all([slack_first, mail_failed, slack_latest])
    db_session.commit()
    db_session.refresh(slack_latest)

    response = client.get('/api/v1/agent-runs/summary')

    assert response.status_code == 200
    payload = response.json()
    assert payload['totals'] == {
        'total_runs': 3,
        'total_tokens': 1800,
        'estimated_cost_usd': 0.00038,
        'average_tokens_per_run': 600,
        'average_cost_per_run': 0.000127,
        'cache_hits': 2,
        'cache_hit_rate': 0.6667,
    }
    assert payload['by_status'] == {'complete': 2, 'failed': 1}
    assert payload['by_agent'] == [
        {
            'agent_name': 'slack_agent',
            'run_count': 2,
            'total_tokens': 1420,
            'estimated_cost_usd': 0.00029,
            'average_tokens_per_run': 710,
            'latest_run_id': slack_latest.id,
            'latest_status': 'complete',
        },
        {
            'agent_name': 'mail_document_agent',
            'run_count': 1,
            'total_tokens': 380,
            'estimated_cost_usd': 0.00009,
            'average_tokens_per_run': 380,
            'latest_run_id': mail_failed.id,
            'latest_status': 'failed',
        },
    ]
