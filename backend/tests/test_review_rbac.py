from sqlalchemy.orm import Session

from backend.app.models import ReviewItem


def test_employee_cannot_approve_review_item(client, db_session: Session) -> None:
    item = _add_review_item(db_session, permission_level='internal')

    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'jun@paraworks.com'})

    assert response.status_code == 403
    assert response.json()['detail'] == 'Review approval permission required.'


def test_reviewer_can_approve_internal_review_item(client, db_session: Session) -> None:
    item = _add_review_item(db_session, permission_level='internal')

    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'mina@paraworks.com'})

    assert response.status_code == 200
    assert response.json()['status'] == 'approved'
    assert response.json()['reviewer_id'] == 'employee-mina'


def test_reviewer_cannot_approve_restricted_review_item(client, db_session: Session) -> None:
    item = _add_review_item(db_session, permission_level='restricted')

    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'mina@paraworks.com'})

    assert response.status_code == 403
    assert response.json()['detail'] == 'Review approval permission required.'


def test_admin_can_approve_restricted_review_item(client, db_session: Session) -> None:
    item = _add_review_item(db_session, permission_level='restricted')

    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'hanvv-admin'})

    assert response.status_code == 200
    assert response.json()['status'] == 'approved'
    assert response.json()['reviewer_id'] == 'google-hanvv-admin'


def _add_review_item(db_session: Session, *, permission_level: str) -> ReviewItem:
    item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Confirm project timeline',
            'reason': 'Slack and Gmail evidence agree on the project milestone.',
        },
        source_links=['https://slack.mock/team/123'],
        source_snippets=['The milestone date was confirmed in the project channel.'],
        confidence_score=0.88,
        permission_level=permission_level,
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item
