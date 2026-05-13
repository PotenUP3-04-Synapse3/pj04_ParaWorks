from sqlalchemy import select

from backend.app.models import DecisionRecord, HistoryEvent, ReviewItem, TimelineEvent, Todo


def seed_review_item(db_session, *, item_type: str, payload: dict) -> ReviewItem:
    item = ReviewItem(
        item_type=item_type,
        payload=payload,
        source_links=['https://slack.mock/source-1'],
        source_snippets=['source snippet'],
        confidence_score=0.87,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_approve_decision_record_promotes_to_knowledge_table(client, db_session) -> None:
    item = seed_review_item(
        db_session,
        item_type='decision_record',
        payload={
            'title': 'Use Redis for queues',
            'decision_summary': 'Redis should power queue and job progress updates.',
        },
    )

    response = client.post(f'/api/v1/review/{item.id}/approve')

    assert response.status_code == 200
    decision = db_session.scalars(select(DecisionRecord)).one()
    assert decision.title == 'Use Redis for queues'
    assert decision.decision_summary == 'Redis should power queue and job progress updates.'
    assert decision.source_links == ['https://slack.mock/source-1']
    assert decision.source_snippets == ['source snippet']
    assert decision.confidence_score == 0.87
    assert decision.permission_level == 'internal'
    assert decision.review_status == 'approved'


def test_approve_history_event_promotes_to_knowledge_table(client, db_session) -> None:
    item = seed_review_item(
        db_session,
        item_type='history_event',
        payload={
            'title': 'Project Beta scope changed',
            'reason': 'Advanced diff UI moved out of MVP.',
        },
    )

    response = client.post(f'/api/v1/review/{item.id}/approve')

    assert response.status_code == 200
    history_event = db_session.scalars(select(HistoryEvent)).one()
    assert history_event.title == 'Project Beta scope changed'
    assert history_event.reason == 'Advanced diff UI moved out of MVP.'
    assert history_event.source_links == ['https://slack.mock/source-1']
    assert history_event.source_snippets == ['source snippet']
    assert history_event.review_status == 'approved'


def test_approve_todo_promotes_to_knowledge_table(client, db_session) -> None:
    item = seed_review_item(
        db_session,
        item_type='todo',
        payload={
            'title': 'Verify evidence inspection before launch',
            'priority': 'high',
            'priority_reason': 'Evidence must be checked before launch readiness review.',
        },
    )

    response = client.post(f'/api/v1/review/{item.id}/approve')

    assert response.status_code == 200
    todo = db_session.scalars(select(Todo)).one()
    assert todo.title == 'Verify evidence inspection before launch'
    assert todo.priority == 'high'
    assert todo.priority_reason == 'Evidence must be checked before launch readiness review.'
    assert todo.source_links == ['https://slack.mock/source-1']
    assert todo.source_snippets == ['source snippet']
    assert todo.review_status == 'approved'


def test_approve_timeline_event_promotes_to_timeline_table(client, db_session) -> None:
    item = seed_review_item(
        db_session,
        item_type='timeline_event',
        payload={
            'title': 'Customer launch date confirmed',
            'result_summary': 'Slack evidence confirmed the customer launch date and owner.',
        },
    )

    response = client.post(f'/api/v1/review/{item.id}/approve')

    assert response.status_code == 200
    timeline_event = db_session.scalars(select(TimelineEvent)).one()
    assert timeline_event.title == 'Customer launch date confirmed'
    assert timeline_event.result_summary == 'Slack evidence confirmed the customer launch date and owner.'
    assert timeline_event.source_links == ['https://slack.mock/source-1']
    assert timeline_event.source_snippets == ['source snippet']
    assert timeline_event.review_status == 'approved'


def test_bulk_approve_agent_candidates_promotes_only_agent_items(client, db_session) -> None:
    agent_history = seed_review_item(
        db_session,
        item_type='history_event',
        payload={
            'title': 'Redis queue decision captured',
            'summary': 'Slack evidence indicates Redis should support queue progress.',
            'agent_name': 'slack_agent',
        },
    )
    agent_decision = seed_review_item(
        db_session,
        item_type='decision_record',
        payload={
            'title': 'PostgreSQL remains durable store',
            'decision_summary': 'Mail evidence keeps PostgreSQL as source of record.',
            'agent_name': 'mail_document_agent',
        },
    )
    manual_item = seed_review_item(
        db_session,
        item_type='todo',
        payload={
            'title': 'Manual follow-up',
            'priority': 'medium',
            'priority_reason': 'This item was written by a person.',
        },
    )

    response = client.post('/api/v1/review/approve-agent-candidates')

    assert response.status_code == 200
    payload = response.json()
    assert payload['approved_count'] == 2
    assert payload['skipped_count'] == 1
    assert payload['approved_item_ids'] == [agent_history.id, agent_decision.id]
    assert payload['cost_policy'] == {
        'paid_llm_calls': False,
        'embedding_calls': False,
        'requires_human_review_state': True,
    }

    db_session.refresh(agent_history)
    db_session.refresh(agent_decision)
    db_session.refresh(manual_item)
    assert agent_history.status == 'approved'
    assert agent_decision.status == 'approved'
    assert manual_item.status == 'pending_review'

    assert db_session.scalars(select(HistoryEvent)).one().title == 'Redis queue decision captured'
    assert db_session.scalars(select(DecisionRecord)).one().title == 'PostgreSQL remains durable store'
