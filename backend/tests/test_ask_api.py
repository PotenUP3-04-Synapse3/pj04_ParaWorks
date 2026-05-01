from backend.app.models import DecisionRecord


def test_ask_api_answers_with_visible_sources(client) -> None:
    client.post('/api/v1/integrations/gmail/sync')

    response = client.post(
        '/api/v1/ask',
        headers={'X-Demo-User': 'viewer'},
        json={'question': 'Redis job state'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['agent_name'] == 'rag_orchestrator_agent'
    assert payload['answer']
    assert payload['source_links']
    assert payload['estimated_cost_usd'] > 0
    assert payload['token_usage']['total_tokens'] > 0


def test_ask_api_respects_viewer_permissions(client) -> None:
    client.post('/api/v1/integrations/drive/sync')

    response = client.post(
        '/api/v1/ask',
        headers={'X-Demo-User': 'viewer'},
        json={'question': 'confidential pricing'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['source_links'] == []
    assert payload['hidden_match_count'] == 1
    assert payload['permission_notice'] == 'Some sources may be hidden by permissions.'


def test_ask_api_answers_from_approved_knowledge(client, db_session) -> None:
    db_session.add(
        DecisionRecord(
            title='Use Redis for queues',
            decision_summary='Redis should power queue and job progress updates.',
            source_links=['https://knowledge.mock/redis-decision'],
            source_snippets=['Approved Redis decision snippet'],
            confidence_score=0.91,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    response = client.post(
        '/api/v1/ask',
        headers={'X-Demo-User': 'viewer'},
        json={'question': 'Redis queues'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['source_links'] == ['https://knowledge.mock/redis-decision']
    assert payload['source_snippets'] == ['Approved Redis decision snippet']
    assert payload['hidden_match_count'] == 0
