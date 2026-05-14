from sqlalchemy import delete, select

from backend.app.models import Project, ReviewItem, SyncJob


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


def test_duplicate_slack_sync_recreates_agent_reviews_when_review_items_were_deleted(
    client,
    db_session,
) -> None:
    first_sync = client.post('/api/v1/integrations/slack/sync')
    assert first_sync.status_code == 200
    assert first_sync.json()['created_review_items'] >= 1

    db_session.execute(delete(ReviewItem))
    db_session.commit()

    second_sync = client.post('/api/v1/integrations/slack/sync')

    assert second_sync.status_code == 200
    assert second_sync.json()['skipped_events'] > 0
    assert second_sync.json()['agent_generated_items'] >= 1
    agent_item = db_session.scalar(
        select(ReviewItem).where(ReviewItem.payload['agent_name'].as_string() == 'slack_agent')
    )
    assert agent_item is not None
    assert agent_item.status == 'pending_review'


def test_slack_sync_keeps_job_running_until_agent_reviews_are_persisted(
    client,
    db_session,
    monkeypatch,
) -> None:
    from backend.app.api.v1 import integrations as integrations_api

    observed_job_state: dict[str, str | int] = {}

    def fake_run_connector_agent_review(
        *,
        db,
        user,
        settings,
        connector_type: str,
        source_ids: list[str],
    ) -> int:
        job = db.scalar(
            select(SyncJob)
            .where(SyncJob.connector_type == connector_type)
            .order_by(SyncJob.id.desc())
        )
        assert job is not None
        observed_job_state['status'] = job.status
        observed_job_state['message'] = job.message
        observed_job_state['source_count'] = len(source_ids)
        db.add(
            ReviewItem(
                item_type='history_event',
                payload={
                    'title': 'Slack 검토 후보',
                    'summary': 'Slack 동기화 후 Agent 리뷰 후보가 생성됩니다.',
                    'agent_name': 'slack_agent',
                    'source_ids': source_ids[:1],
                },
                source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
                source_snippets=['Slack 동기화 검증용 근거입니다.'],
                confidence_score=0.9,
                permission_level='internal',
                status='pending_review',
            )
        )
        return 1

    monkeypatch.setattr(
        integrations_api,
        '_run_connector_agent_review',
        fake_run_connector_agent_review,
    )

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert observed_job_state['status'] == 'running'
    assert 'agent_review=running' in str(observed_job_state['message'])
    assert observed_job_state['source_count'] > 0
    payload = response.json()
    assert payload['created_review_items'] >= 1
    assert payload['pending_review_count'] == db_session.query(ReviewItem).count()
    assert payload['pending_review_count'] >= 1

    latest_job = db_session.scalar(
        select(SyncJob).where(SyncJob.connector_type == 'slack').order_by(SyncJob.id.desc())
    )
    assert latest_job is not None
    assert latest_job.status == 'complete'
    assert 'created_review_items=' in (latest_job.message or '')


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
