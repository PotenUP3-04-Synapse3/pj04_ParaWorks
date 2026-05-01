from backend.app.models import ReviewItem


def test_approve_review_item_changes_status(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]
    response = client.post(f"/api/v1/review/{item['id']}/approve")
    assert response.status_code == 200
    assert response.json()['status'] == 'approved'


def test_reject_review_item_changes_status(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]
    response = client.post(f"/api/v1/review/{item['id']}/reject")
    assert response.status_code == 200
    assert response.json()['status'] == 'rejected'


def test_patch_review_item_updates_payload(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]

    response = client.patch(f"/api/v1/review/{item['id']}", json={'payload': {'title': 'Updated title'}})

    assert response.status_code == 200
    body = response.json()
    assert body['payload']['title'] == 'Updated title'
    assert body['status'] == 'pending_review'


def test_request_more_evidence_changes_status(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]

    response = client.post(f"/api/v1/review/{item['id']}/request-more-evidence")

    assert response.status_code == 200
    assert response.json()['status'] == 'needs_more_evidence'


def test_review_item_preview_returns_promotion_shape(client, db_session) -> None:
    item = ReviewItem(
        item_type='todo',
        payload={
            'title': 'Follow up on Redis rollout',
            'priority': 'high',
            'priority_reason': 'The queue migration needs owner confirmation.',
        },
        source_links=['https://slack.mock/team/123'],
        source_snippets=['Redis rollout needs a clear owner.'],
        confidence_score=0.87,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    response = client.get(f'/api/v1/review/{item.id}/promotion-preview')

    assert response.status_code == 200
    payload = response.json()
    assert payload['can_approve'] is True
    assert payload['target_type'] == 'todo'
    assert payload['missing_required_fields'] == []
    assert payload['normalized_payload'] == {
        'title': 'Follow up on Redis rollout',
        'priority': 'high',
        'priority_reason': 'The queue migration needs owner confirmation.',
    }


def test_approve_review_item_rejects_missing_required_fields(client, db_session) -> None:
    item = ReviewItem(
        item_type='decision_record',
        payload={'title': 'Use Redis'},
        source_links=['https://slack.mock/team/456'],
        source_snippets=['Redis decision needs a summary.'],
        confidence_score=0.9,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    response = client.post(f'/api/v1/review/{item.id}/approve')

    assert response.status_code == 400
    assert response.json()['detail'] == 'Review item is missing required fields'
