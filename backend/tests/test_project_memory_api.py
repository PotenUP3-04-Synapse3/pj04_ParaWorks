from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.ingestion.service import ingest_events
from backend.app.models import ReviewItem, TimelineEvent
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


def test_projects_api_returns_two_canonical_projects_and_approved_evidence_only(
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
    assert [project['project_key'] for project in payload['projects']] == ['k-tech-pilot', 'seed-ir']
    assert {project['name'] for project in payload['projects']} == {'K테크 파일럿', '시드 투자 IR'}
    assert 'Project Newbiegenie' not in {project['name'] for project in payload['projects']}
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
