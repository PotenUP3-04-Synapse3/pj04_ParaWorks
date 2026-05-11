from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.ingestion.service import ingest_events


def _event(
    *,
    source_type: str,
    source_id: str,
    title: str,
    body: str,
    permission_level: str = 'internal',
    scenario: str = 'project-alpha-redis-decision',
) -> SourceEvent:
    return SourceEvent(
        source_type=source_type,
        source_id=source_id,
        source_url=f'https://{source_type}.mock/project-alpha/{source_id}',
        title=title,
        body=body,
        author='owner@example.com',
        participants=['owner@example.com'],
        timestamp=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        permission_level=permission_level,
        raw_metadata={
            'scenario': scenario,
            'project_key': scenario,
            'sync_partition': source_type,
            'sync_cursor': '2026-05-01T09:00:00Z',
        },
    )


def test_projects_api_groups_gmail_drive_and_calendar_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    ingest_events(
        db_session,
        [
            _event(
                source_type='gmail',
                source_id='gmail-alpha-summary',
                title='Project Alpha Redis summary',
                body='Redis keeps transient job state while PostgreSQL remains the source of record.',
            ),
            _event(
                source_type='drive',
                source_id='drive-alpha-architecture-note',
                title='Project Alpha architecture note',
                body='Architecture note confirms Redis-backed status updates.',
                permission_level='restricted',
            ),
            _event(
                source_type='calendar',
                source_id='calendar-alpha-review',
                title='Project Alpha decision review',
                body='Meeting reviewed the Redis and PostgreSQL responsibility split.',
            ),
        ],
    )

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['project_count'] == 1
    project = payload['projects'][0]
    assert project['project_key'] == 'project-alpha-redis-decision'
    assert project['name'] == 'Project Alpha Redis Decision'
    assert project['source_types'] == ['calendar', 'drive', 'gmail']
    assert project['evidence_count'] == 3
    assert project['permission_level'] == 'restricted'
    assert project['summary'] == (
        'Project Alpha Redis summary, Project Alpha architecture note, '
        'Project Alpha decision review 증거가 하나의 프로젝트 흐름으로 묶였습니다.'
    )
    assert len(project['evidence']) == 3
    assert {item['source_type'] for item in project['evidence']} == {'gmail', 'drive', 'calendar'}


def test_projects_api_hides_restricted_project_from_internal_user(
    client: TestClient,
    db_session: Session,
) -> None:
    ingest_events(
        db_session,
        [
            _event(
                source_type='drive',
                source_id='drive-restricted-plan',
                title='Restricted launch plan',
                body='Restricted pricing and launch evidence.',
                permission_level='restricted',
                scenario='restricted-launch-plan',
            )
        ],
    )

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'hanvv-employee'})

    assert response.status_code == 200
    assert response.json()['projects'] == []
    assert response.json()['hidden_project_count'] == 1
