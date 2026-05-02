from sqlalchemy import select

from backend.app.models import AuditLog, ReviewItem


def seed_review_item(db_session) -> ReviewItem:
    item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Redis queue decision captured',
            'reason': 'Slack evidence indicates Redis should support queue progress.',
        },
        source_links=['https://slack.mock/source-1'],
        source_snippets=['source snippet'],
        confidence_score=0.87,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_review_approval_records_admin_audit_log(client, db_session) -> None:
    item = seed_review_item(db_session)

    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'admin'})

    assert response.status_code == 200
    audit = db_session.scalars(select(AuditLog)).one()
    assert audit.actor_email == 'admin@paraworks.com'
    assert audit.actor_role == 'admin'
    assert audit.action == 'review.approve'
    assert audit.target_type == 'review_item'
    assert audit.target_id == str(item.id)
    assert audit.status == 'success'
    assert audit.metadata_['item_type'] == 'history_event'


def test_connector_sync_records_audit_log(client, db_session) -> None:
    response = client.post('/api/v1/integrations/slack/sync', headers={'X-Demo-User': 'admin'})

    assert response.status_code == 200
    audit = db_session.scalars(select(AuditLog)).one()
    assert audit.action == 'integration.sync'
    assert audit.target_type == 'connector'
    assert audit.target_id == 'slack'
    assert audit.metadata_['job_id'] == response.json()['job_id']
    assert audit.metadata_['created_review_items'] == response.json()['created_review_items']


def test_company_memory_run_records_audit_log(client, db_session) -> None:
    response = client.post(
        '/api/v1/orchestration/company-memory/run',
        json={'question': 'Redis job state'},
        headers={'X-Demo-User': 'admin'},
    )

    assert response.status_code == 200
    audit = db_session.scalars(select(AuditLog)).one()
    assert audit.action == 'orchestration.company_memory.run'
    assert audit.target_type == 'workflow'
    assert audit.target_id == 'company_memory'
    assert audit.metadata_['backend'] == 'langgraph'
    assert audit.metadata_['rag_agent_run_created'] is True


def test_rag_reindex_job_creation_records_audit_log(client, db_session) -> None:
    response = client.post('/api/v1/rag/reindex/jobs?dry_run=true', headers={'X-Demo-User': 'admin'})

    assert response.status_code == 200
    audit = db_session.scalars(select(AuditLog)).one()
    assert audit.action == 'rag.reindex.job.create'
    assert audit.target_type == 'rag-index'
    assert audit.target_id == response.json()['job_id']
    assert audit.metadata_['dry_run'] is True


def test_admin_can_list_audit_logs(client, db_session) -> None:
    item = seed_review_item(db_session)
    client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'admin'})

    response = client.get('/api/v1/admin/audit-logs', headers={'X-Demo-User': 'admin'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['logs'][0]['action'] == 'review.approve'
    assert payload['logs'][0]['actor_email'] == 'admin@paraworks.com'
    assert payload['logs'][0]['metadata']['item_type'] == 'history_event'


def test_employee_cannot_list_audit_logs(client, db_session) -> None:
    response = client.get('/api/v1/admin/audit-logs', headers={'X-Demo-User': 'viewer'})

    assert response.status_code == 403
