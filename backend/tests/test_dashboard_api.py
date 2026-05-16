from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from backend.app.models import (
    DecisionRecord,
    Project,
    ReviewItem,
    Source,
    TimelineEvent,
    Todo,
)


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


def test_dashboard_today_todos_uses_approved_open_todos_due_from_today(client, db_session) -> None:
    today = datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    upcoming = '2099-01-01'
    project = Project(
        project_key='project-alpha',
        name='Project Alpha',
        summary='고객사 공유본 프로젝트입니다.',
    )
    due_today = Todo(
        project_key='project-alpha',
        title='오늘 고객사 공유본 보내기',
        assignee='김하나',
        due_date=today,
        priority='high',
        priority_reason='오늘까지 공유본 발송이 필요합니다.',
        source_links=['https://slack.mock/today'],
        source_snippets=['오늘 공유본을 보내주세요.'],
        confidence_score=0.88,
        permission_level='internal',
        review_status='approved',
    )
    due_upcoming = Todo(
        project_key=None,
        title='다가오는 고객사 회신 준비',
        assignee='김하나',
        due_date=upcoming,
        priority='medium',
        priority_reason='고객사 회신 준비가 필요합니다.',
        source_links=['https://slack.mock/upcoming'],
        source_snippets=['다가오는 회신을 준비해주세요.'],
        confidence_score=0.82,
        permission_level='internal',
        review_status='approved',
    )
    pending_today = Todo(
        title='아직 검토 중인 오늘 업무',
        assignee='김하나',
        due_date=today,
        priority='medium',
        priority_reason='검토 전입니다.',
        source_links=['https://slack.mock/pending'],
        source_snippets=['검토 전입니다.'],
        confidence_score=0.8,
        permission_level='internal',
        review_status='pending_review',
    )
    completed = Todo(
        title='이미 완료한 오늘 업무',
        assignee='김하나',
        due_date=today,
        completed_at=datetime.now(UTC),
        completed_by='demo-admin',
        priority='medium',
        priority_reason='완료된 업무입니다.',
        source_links=['https://slack.mock/completed'],
        source_snippets=['완료된 업무입니다.'],
        confidence_score=0.8,
        permission_level='internal',
        review_status='approved',
    )
    past = Todo(
        title='이미 지난 업무',
        assignee='김하나',
        due_date='2000-01-01',
        priority='medium',
        priority_reason='지난 업무입니다.',
        source_links=['https://slack.mock/past'],
        source_snippets=['지난 업무입니다.'],
        confidence_score=0.8,
        permission_level='internal',
        review_status='approved',
    )
    db_session.add_all([project, due_today, due_upcoming, pending_today, completed, past])
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
            'completed_at': None,
        },
        {
            'id': due_upcoming.id,
            'title': '다가오는 고객사 회신 준비',
            'assignee': '김하나',
            'due_date': upcoming,
            'category': '프로젝트 미지정',
            'priority': 'medium',
            'completed_at': None,
        },
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


def test_dashboard_today_events_lists_today_calendar_sources_only(client, db_session) -> None:
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    yesterday_start = f'{(today - timedelta(days=1)).isoformat()}T09:00:00+09:00'
    today_start = f'{today.isoformat()}T10:30:00+09:00'
    today_fallback_start = f'{today.isoformat()}T13:00:00+09:00'
    tomorrow_start = f'{(today + timedelta(days=1)).isoformat()}T09:00:00+09:00'
    today_event = Source(
        source_type='calendar',
        source_id='calendar:primary:today-event',
        source_url='https://calendar.google.com/event?eid=today',
        title='Customer renewal meeting',
        author='organizer@example.com',
        permission_level='internal',
        raw_metadata={
            'event_start': today_start,
            'event_end': f'{today.isoformat()}T11:00:00+09:00',
            'location': 'Zoom',
            'organizer_email': 'organizer@example.com',
            'calendar_attendee_summary': '2 accepted, 1 tentative',
        },
    )
    fallback_event = Source(
        source_type='calendar',
        source_id='calendar:primary:today-fallback-event',
        source_url='https://calendar.google.com/event?eid=today-fallback',
        title='Fallback start meeting',
        author='lead@example.com',
        permission_level='restricted',
        raw_metadata={
            'start': today_fallback_start,
            'end': f'{today.isoformat()}T13:30:00+09:00',
            'organizer_email': 'lead@example.com',
            'attendee_response_statuses': {'accepted': 1, 'needsAction': 2},
        },
    )

    db_session.add_all(
        [
            today_event,
            fallback_event,
            Source(
                source_type='calendar',
                source_id='calendar:primary:yesterday-event',
                source_url='https://calendar.google.com/event?eid=yesterday',
                title='Yesterday meeting',
                permission_level='internal',
                raw_metadata={'event_start': yesterday_start},
            ),
            Source(
                source_type='calendar',
                source_id='calendar:primary:tomorrow-event',
                source_url='https://calendar.google.com/event?eid=tomorrow',
                title='Tomorrow meeting',
                permission_level='internal',
                raw_metadata={'event_start': tomorrow_start},
            ),
            Source(
                source_type='calendar',
                source_id='calendar:primary:bad-date',
                source_url='https://calendar.google.com/event?eid=bad',
                title='Bad date meeting',
                permission_level='internal',
                raw_metadata={'event_start': 'not-a-date'},
            ),
        ]
    )
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    assert response.json()['today_events'] == [
        {
            'id': today_event.id,
            'title': 'Customer renewal meeting',
            'start': today_start,
            'end': f'{today.isoformat()}T11:00:00+09:00',
            'location': 'Zoom',
            'organizer': 'organizer@example.com',
            'attendee_summary': '2 accepted, 1 tentative',
            'source_url': 'https://calendar.google.com/event?eid=today',
            'permission_level': 'internal',
        },
        {
            'id': fallback_event.id,
            'title': 'Fallback start meeting',
            'start': today_fallback_start,
            'end': f'{today.isoformat()}T13:30:00+09:00',
            'location': '',
            'organizer': 'lead@example.com',
            'attendee_summary': 'accepted 1, needsAction 2',
            'source_url': 'https://calendar.google.com/event?eid=today-fallback',
            'permission_level': 'restricted',
        },
    ]


def test_dashboard_pending_items_match_review_queue_order_and_count(client, db_session) -> None:
    review_items = [
        ReviewItem(
            item_type='timeline_event',
            payload={'title': 'Timeline item'},
            status='pending_review',
            confidence_score=0.9,
            permission_level='internal',
        ),
        ReviewItem(
            item_type='todo',
            payload={'title': 'Todo item'},
            status='pending_review',
            confidence_score=0.9,
            permission_level='internal',
        ),
        ReviewItem(
            item_type='decision_record',
            payload={'title': 'Decision item'},
            status='pending_review',
            confidence_score=0.9,
            permission_level='internal',
        ),
        ReviewItem(
            item_type='history_event',
            payload={'title': 'History item'},
            status='pending_review',
            confidence_score=0.9,
            permission_level='internal',
        ),
    ]
    db_session.add_all(review_items)
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    payload = response.json()
    assert payload['pending_review_count'] == 4
    assert [item['title'] for item in payload['pending_items']] == [
        'Decision item',
        'Todo item',
        'History item',
    ]


def test_dashboard_pending_items_use_review_display_title_and_deep_link(client, db_session) -> None:
    item = ReviewItem(
        item_type='decision_record',
        payload={
            'title': 'ParaWorks source 연결',
            'summary': '실제 검토 큐에 보이는 결정 후보',
        },
        status='pending_review',
        confidence_score=0.9,
        permission_level='internal',
    )
    db_session.add(item)
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    pending_item = response.json()['pending_items'][0]
    assert pending_item['id'] == item.id
    assert pending_item['title'] == '실제 검토 큐에 보이는 결정 후보'
    assert pending_item['review_url'] == f'/review?itemId={item.id}'


def test_dashboard_pending_items_collapse_duplicate_review_groups(client, db_session) -> None:
    duplicate_items = [
        ReviewItem(
            item_type='decision_record',
            payload={'title': 'ParaWorks source 연결', 'summary': '같은 검토 후보'},
            status='pending_review',
            confidence_score=0.9,
            permission_level='internal',
        ),
        ReviewItem(
            item_type='decision_record',
            payload={'title': 'ParaWorks source 연결', 'summary': '같은 검토 후보'},
            status='pending_review',
            confidence_score=0.88,
            permission_level='internal',
        ),
        ReviewItem(
            item_type='todo',
            payload={'title': '다른 검토 후보'},
            status='pending_review',
            confidence_score=0.82,
            permission_level='internal',
        ),
    ]
    db_session.add_all(duplicate_items)
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    payload = response.json()
    assert payload['pending_review_count'] == 3
    assert [item['title'] for item in payload['pending_items']] == [
        '같은 검토 후보',
        '다른 검토 후보',
    ]


def test_dashboard_calendar_events_include_synced_events_beyond_today(client, db_session) -> None:
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    tomorrow_start = f'{(today + timedelta(days=1)).isoformat()}T14:00:00+09:00'
    next_week_start = f'{(today + timedelta(days=7)).isoformat()}T10:00:00+09:00'
    tomorrow_event = Source(
        source_type='calendar',
        source_id='calendar:primary:tomorrow-dashboard',
        source_url='https://calendar.google.com/event?eid=tomorrow-dashboard',
        title='Tomorrow dashboard event',
        author='organizer@example.com',
        permission_level='internal',
        raw_metadata={
            'event_start': tomorrow_start,
            'event_end': f'{(today + timedelta(days=1)).isoformat()}T15:00:00+09:00',
            'organizer_email': 'organizer@example.com',
            'calendar_attendee_summary': '1 accepted',
        },
    )
    next_week_event = Source(
        source_type='calendar',
        source_id='calendar:primary:next-week-dashboard',
        source_url='https://calendar.google.com/event?eid=next-week-dashboard',
        title='Next week dashboard event',
        permission_level='internal',
        raw_metadata={
            'event_start': next_week_start,
            'event_end': f'{(today + timedelta(days=7)).isoformat()}T11:00:00+09:00',
        },
    )
    db_session.add_all([next_week_event, tomorrow_event])
    db_session.commit()

    response = client.get('/api/v1/dashboard')

    assert response.status_code == 200
    payload = response.json()
    assert payload['today_events'] == []
    assert payload['calendar_events'] == [
        {
            'id': tomorrow_event.id,
            'title': 'Tomorrow dashboard event',
            'start': tomorrow_start,
            'end': f'{(today + timedelta(days=1)).isoformat()}T15:00:00+09:00',
            'location': '',
            'organizer': 'organizer@example.com',
            'attendee_summary': '1 accepted',
            'source_url': 'https://calendar.google.com/event?eid=tomorrow-dashboard',
            'permission_level': 'internal',
        },
        {
            'id': next_week_event.id,
            'title': 'Next week dashboard event',
            'start': next_week_start,
            'end': f'{(today + timedelta(days=7)).isoformat()}T11:00:00+09:00',
            'location': '',
            'organizer': '',
            'attendee_summary': '',
            'source_url': 'https://calendar.google.com/event?eid=next-week-dashboard',
            'permission_level': 'internal',
        },
    ]
