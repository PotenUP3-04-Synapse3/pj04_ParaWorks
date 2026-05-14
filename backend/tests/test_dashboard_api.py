from backend.app.models import DecisionRecord, TimelineEvent


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
