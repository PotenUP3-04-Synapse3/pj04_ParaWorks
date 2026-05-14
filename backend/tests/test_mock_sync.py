from sqlalchemy import select

from backend.app.models import Project, ReviewItem


def test_mock_slack_sync_creates_pending_review_items(client) -> None:
    response = client.post('/api/v1/integrations/slack/sync')
    assert response.status_code == 200
    assert response.json()['status'] == 'complete'

    review_response = client.get('/api/v1/review?status=pending_review')
    assert review_response.status_code == 200
    assert review_response.json()['items']


def test_sync_creates_project_assignment_review_items_for_defined_projects(client, db_session) -> None:
    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis job status and worker queue architecture project',
        )
    )
    db_session.commit()

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert response.json()['created_review_items'] >= 1
    assignment = db_session.scalar(
        select(ReviewItem).where(
            ReviewItem.item_type == 'project_assignment',
            ReviewItem.payload['project_key'].as_string() == 'project-alpha',
        )
    )
    assert assignment is not None
    assert assignment.status == 'pending_review'


def test_duplicate_sync_still_classifies_existing_sources_for_new_project(client, db_session) -> None:
    first_sync = client.post('/api/v1/integrations/slack/sync')
    assert first_sync.status_code == 200

    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis job status and worker queue architecture project',
        )
    )
    db_session.commit()

    second_sync = client.post('/api/v1/integrations/slack/sync')

    assert second_sync.status_code == 200
    assert second_sync.json()['skipped_events'] > 0
    assert second_sync.json()['project_assignment_items'] >= 1
    assignment = db_session.scalar(
        select(ReviewItem).where(
            ReviewItem.item_type == 'project_assignment',
            ReviewItem.payload['project_key'].as_string() == 'project-alpha',
        )
    )
    assert assignment is not None
    assert assignment.status == 'pending_review'


def test_production_like_sync_requires_real_connection(monkeypatch, client) -> None:
    from backend.app.core.config import get_settings

    monkeypatch.setenv('PARAWORKS_DEMO_MODE', 'false')
    monkeypatch.setenv('SLACK_BOT_TOKEN', '')
    get_settings.cache_clear()
    login_response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})
    assert login_response.status_code == 200

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 409
    assert 'not connected' in response.json()['detail']
