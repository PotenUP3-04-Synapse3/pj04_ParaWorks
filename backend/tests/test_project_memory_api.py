from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.ingestion.service import ingest_events
from backend.app.models import Project, ReviewItem, TimelineEvent
from backend.app.projects.classifier import build_project_assignment_candidates


def _event(
    *,
    source_type: str,
    source_id: str,
    title: str,
    body: str,
    permission_level: str = 'internal',
    source_url: str | None = None,
) -> SourceEvent:
    return SourceEvent(
        source_type=source_type,
        source_id=source_id,
        source_url=source_url or f'https://{source_type}.mock/{source_id}',
        title=title,
        body=body,
        author='owner@example.com',
        participants=['owner@example.com'],
        timestamp=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        permission_level=permission_level,
        raw_metadata={
            'sync_partition': source_type,
            'sync_cursor': '2026-05-01T09:00:00Z',
        },
    )


def test_project_classifier_finds_ktech_and_ir_but_excludes_company_rules(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            Project(
                project_key='k-tech-pilot',
                name='K테크 파일럿',
                summary='K테크 솔루션즈 파일럿과 온보딩 프로젝트',
            ),
            Project(
                project_key='seed-ir',
                name='시드 투자 IR',
                summary='Series Seed IR, VC 미팅, 피치덱 준비 프로젝트',
            ),
        ]
    )
    ingest_events(
        db_session,
        [
            _event(
                source_type='drive',
                source_id='drive-ktech-plan',
                title='02_파일럿_프로젝트/K테크 온보딩 계획',
                body='K테크 솔루션즈 파일럿은 3개월 일정으로 진행한다.',
            ),
            _event(
                source_type='gmail',
                source_id='gmail-ir-followup',
                title='Series Seed IR 후속 요청',
                body='VC 미팅 전 피치덱과 재무 프로젝션을 검토한다.',
            ),
            _event(
                source_type='drive',
                source_id='drive-company-rule',
                title='00_회사규정/휴가 정책',
                body='회사 공통 휴가 정책 문서입니다.',
            ),
        ],
    )

    candidates = build_project_assignment_candidates(db_session)

    assert {candidate.project_key for candidate in candidates} == {'k-tech-pilot', 'seed-ir'}
    assert all('00_회사규정' not in candidate.source_title for candidate in candidates)


def test_project_classifier_matches_bracketed_ir_gmail_subject(db_session: Session) -> None:
    db_session.add(
        Project(
            project_key='seed-ir',
            name='시드 투자 IR',
            summary='Series Seed IR, VC 미팅, 피치덱 준비 프로젝트',
        )
    )
    ingest_events(
        db_session,
        [
            _event(
                source_type='gmail',
                source_id='gmail-bracket-ir',
                title='[IR] A벤처스 미팅 결과 공유 및 액션 아이템',
                body='시드 투자 IR 후속 미팅 전까지 피치덱 수정안을 준비한다.',
            )
        ],
    )

    candidates = build_project_assignment_candidates(db_session)

    assert len(candidates) == 1
    assert candidates[0].project_key == 'seed-ir'
    assert candidates[0].source_type == 'gmail'


def test_projects_reclassify_creates_pending_review_without_tokens(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='k-tech-pilot',
            name='K테크 파일럿',
            summary='K테크 파일럿 제안서와 온보딩 프로젝트',
        )
    )
    ingest_events(
        db_session,
        [
            _event(
                source_type='slack',
                source_id='slack-ktech-deadline',
                title='Slack message in C0AUJDZUKA8',
                body='K테크 파일럿 제안서는 금요일까지 업데이트해 주세요.',
                source_url='https://slack.mock/archives/C0AUJDZUKA8/p1',
            )
        ],
    )

    dry_run = client.post('/api/v1/projects/reclassify?dry_run=true', headers={'X-Demo-User': 'demo-admin'})
    execute = client.post('/api/v1/projects/reclassify?dry_run=false', headers={'X-Demo-User': 'demo-admin'})

    assert dry_run.status_code == 200
    assert dry_run.json()['candidate_count'] == 1
    assert dry_run.json()['created_review_items'] == 0
    assert dry_run.json()['cost_policy']['estimated_input_tokens'] == 0
    assert execute.status_code == 200
    assert execute.json()['created_review_items'] == 1
    item = db_session.query(ReviewItem).filter_by(item_type='project_assignment').one()
    assert item.status == 'pending_review'
    assert item.payload['project_key'] == 'k-tech-pilot'
    assert item.source_snippets


def test_created_project_is_visible_without_approved_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='project-empty-client-portal',
            name='고객 포털 개편',
            summary='고객이 계약 문서와 처리 상태를 확인하는 포털을 개편한다.',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    project = next(project for project in response.json()['projects'] if project['project_key'] == 'project-empty-client-portal')
    assert project['name'] == '고객 포털 개편'
    assert project['summary']
    assert project['evidence_count'] == 0
    assert project['timeline_items'] == []


def test_defined_projects_excludes_hardcoded_projects(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='project-client-portal',
            name='고객 포털 개편',
            summary='고객 포털 프로젝트',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects/defined', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    assert response.json()['projects'] == [
        {
            'project_key': 'project-client-portal',
            'name': '고객 포털 개편',
            'summary': '고객 포털 프로젝트',
        }
    ]


def test_define_project_then_projects_api_returns_empty_project(
    client: TestClient,
) -> None:
    create_response = client.post(
        '/api/v1/projects/define',
        headers={'X-Demo-User': 'demo-admin'},
        json={
            'name': '정산 자동화',
            'summary': '정산 파일 검토와 승인 흐름을 자동화하는 프로젝트',
        },
    )

    assert create_response.status_code == 200
    project_key = create_response.json()['project']['project_key']

    list_response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert list_response.status_code == 200
    project = next(project for project in list_response.json()['projects'] if project['project_key'] == project_key)
    assert project['name'] == '정산 자동화'
    assert project['evidence_count'] == 0
    assert project['timeline_items'] == []


def test_define_project_returns_readable_empty_summary(client: TestClient) -> None:
    create_response = client.post(
        '/api/v1/projects/define',
        headers={'X-Demo-User': 'demo-admin'},
        json={
            'name': '정산 자동화',
            'summary': '정산 파일 검토와 승인 흐름을 자동화하는 프로젝트',
        },
    )

    assert create_response.status_code == 200
    project_key = create_response.json()['project']['project_key']

    list_response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert list_response.status_code == 200
    project = next(project for project in list_response.json()['projects'] if project['project_key'] == project_key)
    assert project['summary'] == '정산 파일 검토와 승인 흐름을 자동화하는 프로젝트 아직 승인된 프로젝트 근거가 없습니다.'
    assert '?' not in project['summary']
    assert 'evidence' not in project['summary']


def test_define_project_creates_pending_assignment_candidates_from_existing_sources(
    client: TestClient,
    db_session: Session,
) -> None:
    ingest_events(
        db_session,
        [
            _event(
                source_type='slack',
                source_id='slack-settlement-automation',
                title='정산 자동화 일정',
                body='정산 자동화 프로젝트는 이번 주에 거래처 파일 검토 화면부터 진행합니다.',
                source_url='https://slack.mock/archives/C123/p1',
            )
        ],
    )

    create_response = client.post(
        '/api/v1/projects/define',
        headers={'X-Demo-User': 'demo-admin'},
        json={
            'name': '정산 자동화',
            'summary': '거래처 파일 검토와 승인 흐름을 자동화하는 프로젝트',
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()['created_review_items'] == 1
    item = db_session.query(ReviewItem).filter_by(item_type='project_assignment').one()
    assert item.status == 'pending_review'
    assert item.payload['project_name'] == '정산 자동화'
    assert item.payload['project_key'] == create_response.json()['project']['project_key']


def test_project_classifier_uses_user_defined_projects(
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='project-client-portal',
            name='고객 포털 개편',
            summary='계약 문서와 진행 상태를 고객에게 보여주는 포털',
        )
    )
    ingest_events(
        db_session,
        [
            _event(
                source_type='slack',
                source_id='slack-client-portal',
                title='고객 포털 개편 일정',
                body='고객 포털 개편은 이번 주에 계약 문서 화면부터 진행합니다.',
                source_url='https://slack.mock/archives/C123/p1',
            )
        ],
    )

    candidates = build_project_assignment_candidates(db_session)

    assert len(candidates) == 1
    assert candidates[0].project_key == 'project-client-portal'
    assert candidates[0].project_name == '고객 포털 개편'


def test_projects_api_returns_approved_project_evidence_only(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        ReviewItem(
            item_type='project_assignment',
            payload={
                'title': 'K테크 파일럿 source 연결',
                'summary': 'K테크 파일럿 제안서 업데이트',
                'project_key': 'k-tech-pilot',
                'project_name': 'K테크 파일럿',
                'source_id': 'slack-ktech-deadline',
                'source_type': 'slack',
                'source_title': 'Slack message in C0AUJDZUKA8',
                'task_summary': 'K테크 파일럿 제안서 업데이트',
                'evidence_reason': '"K테크" 단서가 발견되었습니다.',
                'timestamp': '2026-05-01T09:00:00Z',
            },
            source_links=['https://slack.mock/archives/C0AUJDZUKA8/p1'],
            source_snippets=['K테크 파일럿 제안서는 금요일까지 업데이트해 주세요.'],
            confidence_score=0.88,
            permission_level='internal',
            status='approved',
        )
    )
    db_session.add(
        ReviewItem(
            item_type='project_assignment',
            payload={
                'title': '프로젝트 결과 source 연결',
                'summary': '잘못된 더미 프로젝트 후보',
                'project_key': 'project-newbiegenie',
                'project_name': 'Project Newbiegenie',
                'source_id': 'dummy',
                'evidence_reason': 'legacy dummy',
            },
            source_links=['https://example.com/dummy'],
            source_snippets=['dummy'],
            confidence_score=0.1,
            permission_level='internal',
            status='approved',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['project_count'] == 2
    assert [project['project_key'] for project in payload['projects']] == ['k-tech-pilot', 'project-newbiegenie']
    assert {project['name'] for project in payload['projects']} == {'K테크 파일럿', 'Project Newbiegenie'}
    ktech = payload['projects'][0]
    assert ktech['evidence_count'] == 1
    assert ktech['evidence'][0]['title'] == 'K테크 파일럿 제안서 업데이트'
    assert ktech['evidence'][0]['evidence_reason']



def test_projects_api_links_timeline_items_to_approved_project_assignments(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        ReviewItem(
            item_type='project_assignment',
            payload={
                'title': 'IR source 연결',
                'summary': 'IR 피치덱 검토',
                'project_key': 'seed-ir',
                'project_name': '시드 투자 IR',
                'source_id': 'drive-ir-deck',
                'source_type': 'drive',
                'source_title': '03_IR_투자/피치덱',
                'task_summary': 'IR 피치덱 검토',
                'evidence_reason': '"IR" 단서가 발견되었습니다.',
                'timestamp': '2026-05-01T09:00:00Z',
            },
            source_links=['https://drive.mock/drive-ir-deck'],
            source_snippets=['IR 피치덱 검토 일정은 다음 주입니다.'],
            confidence_score=0.88,
            permission_level='internal',
            status='approved',
        )
    )
    db_session.add(
        TimelineEvent(
            title='IR 피치덱 검토 완료',
            result_summary='투자자 미팅 전 피치덱 검토를 완료했다.',
            source_links=['https://drive.mock/drive-ir-deck'],
            source_snippets=['IR 피치덱 검토 일정은 다음 주입니다.'],
            confidence_score=0.9,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    seed_ir = next(project for project in response.json()['projects'] if project['project_key'] == 'seed-ir')
    assert len(seed_ir['timeline_items']) == 1
    assert seed_ir['timeline_items'][0]['title'] == 'IR 피치덱 검토 완료'


def test_projects_api_links_approved_timeline_by_project_key_without_assignment(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        TimelineEvent(
            project_key='seed-ir',
            title='IR pitch deck review completed',
            result_summary='Investor meeting pitch deck review was completed.',
            source_links=['https://drive.mock/drive-ir-deck'],
            source_snippets=['IR pitch deck review is scheduled for next week.'],
            confidence_score=0.9,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    payload = response.json()
    seed_ir = next(project for project in payload['projects'] if project['project_key'] == 'seed-ir')
    assert seed_ir['evidence_count'] == 0
    assert len(seed_ir['timeline_items']) == 1
    assert seed_ir['timeline_items'][0]['title'] == 'IR pitch deck review completed'
    assert seed_ir['timeline_items'][0]['project_key'] == 'seed-ir'


def test_approved_review_item_with_project_key_appears_in_project_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    review_item = ReviewItem(
        item_type='timeline_event',
        payload={
            'title': 'K-Tech proposal deadline confirmed',
            'result_summary': 'K-Tech pilot proposal deadline was confirmed for Friday.',
            'project_key': 'k-tech-pilot',
        },
        source_links=['https://slack.mock/archives/C0AUJDZUKA8/p1'],
        source_snippets=['Please update the K-Tech pilot proposal by Friday.'],
        confidence_score=0.88,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(review_item)
    db_session.commit()
    db_session.refresh(review_item)

    approve_response = client.post(
        f'/api/v1/review/{review_item.id}/approve',
        headers={'X-Demo-User': 'demo-admin'},
    )
    assert approve_response.status_code == 200

    projects_response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert projects_response.status_code == 200
    ktech = next(project for project in projects_response.json()['projects'] if project['project_key'] == 'k-tech-pilot')
    assert [item['title'] for item in ktech['timeline_items']] == ['K-Tech proposal deadline confirmed']
    assert ktech['timeline_items'][0]['project_key'] == 'k-tech-pilot'


def test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    review_item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Seed IR follow-up schedule changed',
            'reason': 'Follow-up meeting schedule changed after investor request.',
            'project_key': 'seed-ir',
        },
        source_links=['https://gmail.mock/message-ir'],
        source_snippets=['The next meeting schedule should be adjusted after the investor request.'],
        confidence_score=0.86,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(review_item)
    db_session.commit()
    db_session.refresh(review_item)

    approve_response = client.post(
        f'/api/v1/review/{review_item.id}/approve',
        headers={'X-Demo-User': 'demo-admin'},
    )
    assert approve_response.status_code == 200

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    seed_ir = next(project for project in response.json()['projects'] if project['project_key'] == 'seed-ir')
    assert seed_ir['evidence_count'] == 0
    assert {item['item_type'] for item in seed_ir['timeline_items']} == {'history_event', 'timeline_event'}
