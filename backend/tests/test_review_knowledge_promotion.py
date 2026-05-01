from sqlalchemy import select

from backend.app.models import DecisionRecord, HistoryEvent, ReviewItem, Todo


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
