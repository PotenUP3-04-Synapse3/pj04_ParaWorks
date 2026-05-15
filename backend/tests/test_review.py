from sqlalchemy import select

from backend.app.models import (
    AgentRun,
    AuditLog,
    Document,
    DocumentChunk,
    DocumentVersion,
    Project,
    ReviewItem,
    Source,
    TimelineEvent,
    Todo,
)


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


def test_reject_mail_document_review_item_preserves_source_evidence(client, db_session) -> None:
    source = Source(
        source_type='gmail',
        source_id='gmail:reject-preserve',
        source_url='https://gmail.mock/reject-preserve',
        title='Reject preserve source',
        author='owner@example.com',
        permission_level='internal',
        raw_metadata={},
    )
    db_session.add(source)
    db_session.flush()
    document = Document(source_id=source.id, title=source.title, current_version='v1')
    db_session.add(document)
    db_session.flush()
    version = DocumentVersion(document_id=document.id, version='v1', body='Rejecting the AI candidate must not delete this source.')
    db_session.add(version)
    db_session.flush()
    chunk = DocumentChunk(
        version_id=version.id,
        source_id=source.id,
        chunk_index=0,
        text='Rejecting the AI candidate must not delete this source.',
        source_snippet='Rejecting the AI candidate must not delete this source.',
        permission_level='internal',
        metadata_={'source_type': 'gmail'},
    )
    item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Reject preserve candidate',
            'summary': 'The AI candidate is not trusted yet.',
            'source_ids': ['gmail:reject-preserve'],
        },
        source_links=[source.source_url],
        source_snippets=[chunk.source_snippet],
        confidence_score=0.72,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add_all([chunk, item])
    db_session.commit()
    db_session.refresh(item)

    response = client.post(f'/api/v1/review/{item.id}/reject')

    assert response.status_code == 200
    assert response.json()['status'] == 'rejected'
    assert db_session.scalar(select(Source).where(Source.source_id == 'gmail:reject-preserve')) is not None
    assert db_session.scalar(select(DocumentChunk).where(DocumentChunk.source_id == source.id)) is not None
    audit_log = db_session.scalar(select(AuditLog).where(AuditLog.action == 'review.reject'))
    assert audit_log is not None
    assert audit_log.metadata_['source_ids_preserved'] == ['gmail:reject-preserve']
    assert audit_log.metadata_['rejected_review_item_id'] == item.id


def test_patch_review_item_updates_payload(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]

    response = client.patch(f"/api/v1/review/{item['id']}", json={'payload': {'title': 'Updated title'}})

    assert response.status_code == 200
    body = response.json()
    assert body['payload']['title'] == 'Updated title'
    assert body['status'] == 'pending_review'


def test_patch_review_item_requires_registered_project_key(client, db_session) -> None:
    db_session.add(
        Project(
            project_key='project-client-portal',
            name='고객 포털 개편',
            summary='고객 포털 개편 프로젝트',
        )
    )
    item = ReviewItem(
        item_type='history_event',
        payload={'title': 'Project candidate', 'summary': 'Needs a project.'},
        source_links=['https://slack.mock/team/123'],
        source_snippets=['고객 포털 화면 검토가 필요합니다.'],
        confidence_score=0.8,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    missing = client.patch(f"/api/v1/review/{item.id}", json={'payload': {'project_key': 'project-missing'}})
    valid = client.patch(f"/api/v1/review/{item.id}", json={'payload': {'project_key': 'project-client-portal'}})

    assert missing.status_code == 400
    assert missing.json()['detail'] == 'Project key is not registered'
    assert valid.status_code == 200
    assert valid.json()['payload']['project_key'] == 'project-client-portal'
    assert valid.json()['payload']['project_name'] == '고객 포털 개편'


def test_slack_agent_review_item_requires_project_before_approval(client, db_session) -> None:
    db_session.add(Project(project_key='project-alpha', name='Project Alpha', summary='Redis work'))
    item = ReviewItem(
        item_type='history_event',
        payload={
            'title': '등록 프로젝트 확인 필요',
            'summary': 'Slack Agent가 업무 후보로 판단했지만 프로젝트 선택이 필요합니다.',
            'agent_name': 'slack_agent',
            'project_assignment_method': 'llm_tool',
            'project_needs_user_selection': True,
        },
        source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
        source_snippets=['새 프로젝트로 보이는 업무 논의입니다.'],
        confidence_score=0.82,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    preview = client.get(f'/api/v1/review/{item.id}/promotion-preview')
    blocked = client.post(f'/api/v1/review/{item.id}/approve')
    patched = client.patch(f'/api/v1/review/{item.id}', json={'payload': {'project_key': 'project-alpha'}})
    approved = client.post(f'/api/v1/review/{item.id}/approve')

    assert preview.status_code == 200
    assert preview.json()['can_approve'] is False
    assert 'project_key' in preview.json()['missing_required_fields']
    assert blocked.status_code == 400
    assert patched.status_code == 200
    assert patched.json()['payload']['project_name'] == 'Project Alpha'
    assert approved.status_code == 200
    assert approved.json()['promotion_result']['project_key'] == 'project-alpha'


def test_review_list_supports_limit_offset_metadata(client, db_session) -> None:
    for index in range(3):
        db_session.add(
            ReviewItem(
                item_type='history_event',
                payload={'title': f'Paged item {index}', 'summary': 'Pagination target.'},
                source_links=[f'https://slack.mock/team/{index}'],
                source_snippets=[f'Snippet {index}'],
                confidence_score=0.7,
                permission_level='internal',
                status='pending_review',
            )
        )
    db_session.commit()

    response = client.get('/api/v1/review?status=pending_review&limit=1&offset=1')

    assert response.status_code == 200
    body = response.json()
    assert body['total_count'] == 3
    assert body['limit'] == 1
    assert body['offset'] == 1
    assert body['has_more'] is True
    assert len(body['items']) == 1


def test_review_list_prioritizes_knowledge_candidates_before_project_assignments(
    client,
    db_session,
) -> None:
    knowledge_item = ReviewItem(
        item_type='decision_record',
        payload={
            'title': 'Slack decision candidate',
            'decision_summary': 'Slack Agent extracted this decision.',
        },
        source_links=['https://slack.mock/archives/C123/p1'],
        source_snippets=['Redis queue policy was decided.'],
        confidence_score=0.91,
        permission_level='internal',
        status='pending_review',
    )
    project_assignment = ReviewItem(
        item_type='project_assignment',
        payload={
            'title': 'Project source assignment',
            'summary': 'Project classifier linked this source.',
            'agent_name': 'project_classifier',
        },
        source_links=['https://slack.mock/archives/C123/p2'],
        source_snippets=['Project evidence snippet.'],
        confidence_score=0.88,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add_all([knowledge_item, project_assignment])
    db_session.commit()

    response = client.get('/api/v1/review?status=pending_review&limit=2')

    assert response.status_code == 200
    assert [item['item_type'] for item in response.json()['items']] == [
        'decision_record',
        'project_assignment',
    ]


def test_request_more_evidence_changes_status(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]

    response = client.post(f"/api/v1/review/{item['id']}/request-more-evidence")

    assert response.status_code == 200
    assert response.json()['status'] == 'needs_more_evidence'


def test_bulk_reject_pending_review_items(client, db_session) -> None:
    items = [
        ReviewItem(
            item_type='history_event',
            payload={'title': f'Reject {index}', 'summary': 'Reject in bulk.'},
            source_links=[f'https://slack.mock/reject/{index}'],
            source_snippets=[f'Reject snippet {index}'],
            confidence_score=0.7,
            permission_level='internal',
            status='pending_review',
        )
        for index in range(3)
    ]
    db_session.add_all(items)
    db_session.commit()
    item_ids = [item.id for item in items]

    response = client.post('/api/v1/review/bulk', json={'action': 'reject', 'item_ids': item_ids})

    assert response.status_code == 200
    assert response.json()['rejected_count'] == 3
    assert response.json()['failed_items'] == []
    statuses = db_session.scalars(select(ReviewItem.status).where(ReviewItem.id.in_(item_ids))).all()
    assert statuses == ['rejected', 'rejected', 'rejected']


def test_bulk_approve_reports_items_that_cannot_be_promoted(client, db_session) -> None:
    valid = ReviewItem(
        item_type='todo',
        payload={
            'title': '고객사 공유본 준비',
            'priority': 'high',
            'priority_reason': '금요일까지 고객사 공유본 준비가 필요합니다.',
        },
        source_links=['https://drive.mock/project-alpha/plan'],
        source_snippets=['고객사 공유본을 준비해주세요.'],
        confidence_score=0.88,
        permission_level='internal',
        status='pending_review',
    )
    invalid = ReviewItem(
        item_type='decision_record',
        payload={'title': 'Use Redis'},
        source_links=['https://slack.mock/team/456'],
        source_snippets=['Redis decision needs a summary.'],
        confidence_score=0.9,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add_all([valid, invalid])
    db_session.commit()

    response = client.post('/api/v1/review/bulk', json={'action': 'approve', 'item_ids': [valid.id, invalid.id]})

    assert response.status_code == 200
    body = response.json()
    assert body['approved_count'] == 1
    assert body['failed_items'] == [{'id': invalid.id, 'detail': 'Review item is missing required fields'}]
    assert db_session.get(ReviewItem, valid.id).status == 'approved'
    assert db_session.get(ReviewItem, invalid.id).status == 'pending_review'


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
