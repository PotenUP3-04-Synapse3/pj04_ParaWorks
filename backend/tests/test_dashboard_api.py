from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.models import DecisionRecord, Project, ReviewItem, TimelineEvent


def test_dashboard_recent_timeline_uses_existing_model_fields(client, db_session) -> None:
    decision = DecisionRecord(
        title='Redis 책임 분리',
        decision_summary='Redis는 작업 상태, PostgreSQL은 영구 기록을 맡습니다.',
        source_links=['https://slack.mock/redis'],
        source_snippets=['Redis and PostgreSQL split'],
        confidence_score=0.91,
        permission_level='internal',
        review_status='approved',
    )
    timeline = TimelineEvent(
        title='공유본 준비 업무 생성',
        result_summary='담당자: 김하나, 기한: 2026-05-15',
        source_links=['https://drive.mock/project-alpha/plan'],
        source_snippets=['김하나님은 금요일까지 공유본을 준비해주세요.'],
        confidence_score=0.86,
        permission_level='internal',
        review_status='approved',
    )
    db_session.add_all([decision, timeline])
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    payload = response.json()
    assert payload['recent_decisions'][0]['summary'] == 'Redis는 작업 상태, PostgreSQL은 영구 기록을 맡습니다.'
    assert payload['recent_timeline'][0] == {
        'id': timeline.id,
        'title': '공유본 준비 업무 생성',
        'summary': '담당자: 김하나, 기한: 2026-05-15',
        'created_at': timeline.created_at.isoformat(),
        'confidence_score': 0.86,
        'source_links': ['https://drive.mock/project-alpha/plan'],
    }


def test_dashboard_today_todos_uses_approved_todo_review_items_due_today(client, db_session) -> None:
    today = datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    due_today = ReviewItem(
        item_type='todo',
        payload={
            'title': '오늘 고객사 공유본 보내기',
            'assignee': '김하나',
            'due_date': today,
            'priority': 'high',
            'project_name': 'Project Alpha',
        },
        source_links=['https://slack.mock/today'],
        source_snippets=['오늘 공유본을 보내주세요.'],
        confidence_score=0.88,
        permission_level='internal',
        status='approved',
    )
    pending_today = ReviewItem(
        item_type='todo',
        payload={
            'title': '아직 검토 중인 오늘 업무',
            'assignee': '김하나',
            'due_date': today,
        },
        source_links=['https://slack.mock/pending'],
        source_snippets=['검토 전입니다.'],
        confidence_score=0.8,
        permission_level='internal',
        status='pending_review',
    )
    future = ReviewItem(
        item_type='todo',
        payload={
            'title': '내일 처리할 업무',
            'assignee': '김하나',
            'due_date': '2099-01-01',
        },
        source_links=['https://slack.mock/future'],
        source_snippets=['미래 업무입니다.'],
        confidence_score=0.8,
        permission_level='internal',
        status='approved',
    )
    db_session.add_all([due_today, pending_today, future])
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    assert response.json()['today_todos'] == [
        {
            'id': due_today.id,
            'title': '오늘 고객사 공유본 보내기',
            'assignee': '김하나',
            'due_date': today,
            'category': 'Project Alpha',
            'priority': 'high',
        }
    ]


def test_dashboard_assigned_projects_lists_registered_project_memory(client, db_session) -> None:
    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='승인 활동이 있는 프로젝트입니다.',
        )
    )
    db_session.add(
        TimelineEvent(
            project_key='project-alpha',
            title='프로젝트 활동 승인',
            result_summary='활동이 승인되었습니다.',
            source_links=['https://slack.mock/project-alpha'],
            source_snippets=['프로젝트 활동'],
            confidence_score=0.9,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    assert response.json()['assigned_projects'] == [
        {
            'project_key': 'project-alpha',
            'name': 'Project Alpha',
            'summary': '승인 활동이 있는 프로젝트입니다. 승인된 원본 근거 1건과 승인된 프로젝트 활동 1건이 연결되어 있습니다.',
            'evidence_count': 1,
            'activity_count': 1,
            'pending_review_count': 0,
            'latest_timestamp': response.json()['assigned_projects'][0]['latest_timestamp'],
            'permission_level': 'internal',
        }
    ]
