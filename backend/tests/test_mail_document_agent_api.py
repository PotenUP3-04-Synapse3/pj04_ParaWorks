from sqlalchemy import select

from backend.app.models import DocumentChunk, DocumentParserRun, Source


def test_mail_document_agent_review_endpoint_creates_agent_review_item(client) -> None:
    gmail_sync = client.post('/api/v1/integrations/gmail/sync')
    drive_sync = client.post('/api/v1/integrations/drive/sync')
    assert gmail_sync.status_code == 200
    assert drive_sync.status_code == 200

    response = client.post('/api/v1/integrations/mail-docs/agent-review')

    assert response.status_code == 200
    payload = response.json()
    assert payload['agent_name'] == 'mail_document_agent'
    assert payload['status'] == 'complete'
    assert payload['created_review_items'] == 1

    review_response = client.get('/api/v1/review?status=pending_review')
    assert review_response.status_code == 200
    review_items = review_response.json()['items']
    agent_items = [
        item for item in review_items
        if item['payload'].get('agent_name') == 'mail_document_agent'
    ]
    assert len(agent_items) == 1
    assert agent_items[0]['payload']['agent_run_id']


def test_gmail_sync_smoke_ingests_attachment_metadata_boundary(client, db_session) -> None:
    response = client.post('/api/v1/integrations/gmail/sync')

    assert response.status_code == 200
    payload = response.json()
    assert payload['connector_type'] == 'gmail'
    assert payload['fetched_events'] == 2
    assert payload['parser_status_counts'] == {'metadata_only': 1}

    attachment_source = db_session.scalar(
        select(Source).where(
            Source.source_id == 'gmail_attachment:gmail-project-alpha-redis-summary:att-budget-pdf'
        )
    )
    assert attachment_source is not None
    assert attachment_source.source_type == 'gmail_attachment'
    assert attachment_source.raw_metadata['parent_source_id'] == 'gmail-project-alpha-redis-summary'
    assert attachment_source.raw_metadata['participants'] == [
        'maya@example.com',
        'noah@example.com',
        'lee@example.com',
    ]

    attachment_chunk = db_session.scalar(
        select(DocumentChunk)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_id == attachment_source.source_id)
    )
    assert attachment_chunk is not None
    assert attachment_chunk.permission_level == 'internal'
    assert attachment_chunk.metadata_['source_type'] == 'gmail_attachment'
    assert attachment_chunk.metadata_['parser_name'] == 'gmail_attachment_metadata'
    assert attachment_chunk.metadata_['parser_status'] == 'metadata_only'
    assert attachment_chunk.metadata_['parser_status_reason'] == 'pdf_parser_not_enabled'
    assert attachment_chunk.metadata_['mime_type'] == 'application/pdf'
    assert attachment_chunk.metadata_['content_signature'].endswith(':2048')

    parser_run = db_session.scalar(
        select(DocumentParserRun).where(DocumentParserRun.source_id == attachment_source.id)
    )
    assert parser_run is not None
    assert parser_run.parser_name == 'gmail_attachment_metadata'
    assert parser_run.parser_status == 'metadata_only'
    assert parser_run.parser_status_reason == 'pdf_parser_not_enabled'
    assert parser_run.mime_type == 'application/pdf'
    assert parser_run.document_version_label == '1777540500000'
    assert parser_run.revision_id == 'att-budget-pdf'
    assert parser_run.chunk_count == 1
