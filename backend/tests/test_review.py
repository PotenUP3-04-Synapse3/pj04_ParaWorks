from backend.app.models import AgentRun, ReviewItem, TimelineEvent, Todo


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


def test_request_more_evidence_preserves_reviewer_note(client, db_session) -> None:
    item = ReviewItem(
        item_type='history_event',
        payload={'title': 'Need more context', 'summary': 'Missing source detail.'},
        source_links=['https://slack.mock/team/789'],
        source_snippets=['We need to confirm this with the owner.'],
        confidence_score=0.62,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    response = client.post(
        f'/api/v1/review/{item.id}/request-more-evidence',
        json={'note': '담당자 발언과 결정 근거를 하나 더 찾아주세요.'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'needs_more_evidence'
    assert body['payload']['needs_more_evidence']['note'] == '담당자 발언과 결정 근거를 하나 더 찾아주세요.'
    assert body['payload']['needs_more_evidence']['requested_by'] == 'demo-admin'
    assert body['payload']['needs_more_evidence']['source_count'] == 1


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


def test_review_item_response_includes_structured_source_evidence(client, db_session) -> None:
    agent_run = AgentRun(
        agent_name='slack_agent',
        prompt_version='slack-summary:v1',
        status='complete',
        source_window='slack:live:ranked:2',
        cache_key='cache-source-evidence',
        model_name='fake-model',
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        estimated_cost_usd=0.00001,
        permission_level='internal',
        metadata_={
            'evidence_summary': [
                {
                    'rank': 1,
                    'source_id': 'slack:C123:1710000000.000100',
                    'source_url': 'https://slack.mock/archives/C123/p1710000000000100',
                    'source_type': 'slack',
                    'timestamp': '1710000000.000100',
                    'author': 'U123',
                    'permission_level': 'internal',
                    'importance_score': 95,
                    'parser_status': 'parsed',
                    'section_path': '결정 사항',
                    'evidence_reason': 'Redis rollout owner를 직접 언급합니다.',
                    'snippet': 'Redis rollout decision needs owner confirmation.',
                }
            ]
        },
    )
    db_session.add(agent_run)
    db_session.flush()
    item = ReviewItem(
        item_type='decision_record',
        payload={
            'title': 'Confirm Redis rollout owner',
            'decision_summary': 'Redis rollout needs a named owner.',
            'agent_name': 'slack_agent',
            'agent_run_id': agent_run.id,
        },
        source_links=['https://slack.mock/archives/C123/p1710000000000100'],
        source_snippets=['Redis rollout decision needs owner confirmation.'],
        confidence_score=0.91,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()

    response = client.get('/api/v1/review?status=pending_review')

    assert response.status_code == 200
    body = response.json()['items'][0]
    assert body['agent_run_id'] == agent_run.id
    assert body['source_evidence'] == [
        {
            'index': 1,
            'rank': 1,
            'source_id': 'slack:C123:1710000000.000100',
            'source_url': 'https://slack.mock/archives/C123/p1710000000000100',
            'source_type': 'slack',
            'source_snippet': 'Redis rollout decision needs owner confirmation.',
            'permission_level': 'internal',
            'confidence_score': 0.91,
            'importance_score': 95,
            'timestamp': '1710000000.000100',
            'author': 'U123',
            'agent_run_id': agent_run.id,
            'parser_status': 'parsed',
            'section_path': '결정 사항',
            'evidence_reason': 'Redis rollout owner를 직접 언급합니다.',
        }
    ]


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


def test_approve_todo_promotes_clean_korean_timeline_without_mojibake(client, db_session) -> None:
    item = ReviewItem(
        item_type='todo',
        payload={
            'title': '고객사 공유본 준비',
            'priority': 'high',
            'priority_reason': '금요일까지 고객사 공유본 준비가 필요합니다.',
            'assignee': '김하나',
            'due_date': '2026-05-15',
        },
        source_links=['https://drive.mock/project-alpha/plan'],
        source_snippets=['김하나님은 금요일까지 고객사 공유본을 준비해주세요.'],
        confidence_score=0.88,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    response = client.post(f'/api/v1/review/{item.id}/approve')

    assert response.status_code == 200
    todo = db_session.query(Todo).one()
    timeline = db_session.query(TimelineEvent).one()
    assert todo.title == '고객사 공유본 준비'
    assert timeline.title == '[할 일] 고객사 공유본 준비'
    assert timeline.result_summary == '담당자: 김하나, 기한: 2026-05-15'
    assert '?' not in timeline.title
    assert '?' not in timeline.result_summary
