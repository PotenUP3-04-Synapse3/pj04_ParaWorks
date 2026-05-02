from backend.app.models import DecisionRecord, HistoryEvent, TimelineEvent, Todo


def test_knowledge_api_returns_approved_company_memory(client, db_session) -> None:
    decision = DecisionRecord(
        title='Use Redis for queues',
        decision_summary='Redis should power queue and job progress updates.',
        source_links=['https://slack.mock/redis'],
        source_snippets=['Redis source snippet'],
        confidence_score=0.91,
        permission_level='internal',
        review_status='approved',
    )
    history = HistoryEvent(
        title='Project Beta scope changed',
        reason='Advanced diff UI moved out of MVP.',
        source_links=['https://gmail.mock/scope'],
        source_snippets=['Scope source snippet'],
        confidence_score=0.84,
        permission_level='internal',
        review_status='approved',
    )
    timeline = TimelineEvent(
        title='Launch QA completed',
        result_summary='QA passed and launch preparation moved to review.',
        source_links=['https://calendar.mock/launch'],
        source_snippets=['Timeline source snippet'],
        confidence_score=0.86,
        permission_level='internal',
        review_status='approved',
    )
    todo = Todo(
        title='Verify evidence inspection before launch',
        priority='high',
        priority_reason='Evidence must be checked before launch readiness review.',
        source_links=['https://drive.mock/evidence'],
        source_snippets=['Todo source snippet'],
        confidence_score=0.8,
        permission_level='restricted',
        review_status='approved',
    )
    db_session.add_all([decision, history, timeline, todo])
    db_session.commit()

    response = client.get('/api/v1/knowledge')

    assert response.status_code == 200
    payload = response.json()
    assert payload['counts'] == {
        'decisions': 1,
        'history_events': 1,
        'timeline_events': 1,
        'todos': 1,
    }
    assert payload['decisions'][0]['title'] == 'Use Redis for queues'
    assert payload['decisions'][0]['summary'] == 'Redis should power queue and job progress updates.'
    assert payload['decisions'][0]['source_links'] == ['https://slack.mock/redis']
    assert payload['decisions'][0]['confidence_score'] == 0.91
    assert payload['history_events'][0]['summary'] == 'Advanced diff UI moved out of MVP.'
    assert payload['timeline_events'][0]['title'] == 'Launch QA completed'
    assert payload['timeline_events'][0]['summary'] == 'QA passed and launch preparation moved to review.'
    assert payload['todos'][0]['summary'] == 'Evidence must be checked before launch readiness review.'
    assert payload['todos'][0]['permission_level'] == 'restricted'
    assert payload['todos'][0]['review_status'] == 'approved'
