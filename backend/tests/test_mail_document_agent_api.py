from sqlalchemy import select

from backend.app.api.v1 import integrations
from backend.app.connectors.mock import get_mock_connector
from backend.app.core.config import Settings, get_settings
from backend.app.ingestion.sync import sync_connector_events
from backend.app.models import AgentRun, DocumentChunk, DocumentParserRun, ReviewItem, Source

CSRF_HEADERS = {'X-CSRF-Token': 'test-csrf-token'}


def _set_csrf_cookie(client) -> None:
    client.cookies.set('paraworks_csrf', 'test-csrf-token')


def test_mail_document_agent_review_endpoint_creates_agent_review_item(client, db_session) -> None:
    _set_csrf_cookie(client)
    sync_connector_events(db=db_session, connector=get_mock_connector('gmail'))
    sync_connector_events(db=db_session, connector=get_mock_connector('drive'))

    response = client.post('/api/v1/integrations/mail-docs/agent-review', headers=CSRF_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload['agent_name'] == 'mail_document_agent'
    assert payload['status'] == 'complete'
    assert payload['created_review_items'] == 3

    review_response = client.get('/api/v1/review?status=pending_review')
    assert review_response.status_code == 200
    review_items = review_response.json()['items']
    agent_items = [
        item for item in review_items
        if item['payload'].get('agent_name') == 'mail_document_agent'
    ]
    assert len(agent_items) == 3
    assert all(item['payload']['agent_run_id'] for item in agent_items)
    assert all(len(item['payload']['source_ids']) <= 2 for item in agent_items)


def test_mail_document_llm_preflight_reports_cost_without_provider_call(client, db_session) -> None:
    _set_csrf_cookie(client)
    sync_connector_events(db=db_session, connector=get_mock_connector('gmail'))

    def override_settings() -> Settings:
        return Settings(
            _env_file=None,
            paraworks_demo_mode=False,
            agent_llm_enabled=True,
            agent_llm_provider_order='openai',
            openai_api_key='test-openai-key',
            gemini_api_key=None,
            google_api_key=None,
            agent_llm_max_estimated_cost_usd=0.001,
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/integrations/mail-docs/agent-review/llm/preflight')

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'run'
    assert payload['budget_status'] == 'within_budget'
    assert payload['model_name'] == 'gpt-5.4-mini'
    assert payload['available_providers'] == ['openai']
    assert payload['requires_paid_confirmation'] is True
    assert payload['evidence_message_count'] == 2
    assert payload['source_window'] == 'mail-docs:live:ranked:12'


def test_mail_document_llm_run_requires_paid_confirmation(client, db_session) -> None:
    _set_csrf_cookie(client)
    sync_connector_events(db=db_session, connector=get_mock_connector('gmail'))

    def override_settings() -> Settings:
        return Settings(
            paraworks_demo_mode=False,
            agent_llm_enabled=True,
            openai_api_key='test-openai-key',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.post(
        '/api/v1/integrations/mail-docs/agent-review/llm',
        headers=CSRF_HEADERS,
        json={'confirm_paid_run': False},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Paid LLM run requires confirm_paid_run=true'


def test_mail_document_llm_run_uses_agent_metadata_without_log_path_config(
    client,
    db_session,
    monkeypatch,
) -> None:
    _set_csrf_cookie(client)
    sync_connector_events(db=db_session, connector=get_mock_connector('gmail'))

    def override_settings() -> Settings:
        return Settings(
            paraworks_demo_mode=False,
            agent_llm_enabled=True,
            openai_api_key='test-openai-key',
        )

    client.app.dependency_overrides[get_settings] = override_settings
    monkeypatch.setattr(
        integrations,
        'build_langchain_mail_document_agent_model',
        lambda _settings: integrations.DeterministicMailDocumentAgentModel(),
    )

    response = client.post(
        '/api/v1/integrations/mail-docs/agent-review/llm',
        headers=CSRF_HEADERS,
        json={'confirm_paid_run': True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['created_review_items'] == 1
    agent_run = db_session.query(AgentRun).one()
    assert agent_run.metadata_['source_window'] == 'mail-docs:live:ranked:12'
    assert agent_run.metadata_['message_count'] == 2
    assert agent_run.metadata_['selection_strategy'] == 'source_group'
    assert 'preflight' in payload
    assert not any(field.endswith('_log_path') or field.endswith('_log_file') for field in Settings.model_fields)


def test_mail_document_llm_run_creates_source_group_review_items(
    client,
    db_session,
    monkeypatch,
) -> None:
    _set_csrf_cookie(client)
    sync_connector_events(db=db_session, connector=get_mock_connector('gmail'))
    sync_connector_events(db=db_session, connector=get_mock_connector('drive'))

    def override_settings() -> Settings:
        return Settings(
            _env_file=None,
            paraworks_demo_mode=False,
            agent_llm_enabled=True,
            openai_api_key='test-openai-key',
        )

    client.app.dependency_overrides[get_settings] = override_settings
    monkeypatch.setattr(
        integrations,
        'build_langchain_mail_document_agent_model',
        lambda _settings: integrations.DeterministicMailDocumentAgentModel(),
    )

    response = client.post(
        '/api/v1/integrations/mail-docs/agent-review/llm',
        headers=CSRF_HEADERS,
        json={'confirm_paid_run': True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['created_review_items'] == 3
    review_items = db_session.query(ReviewItem).order_by(ReviewItem.id).all()
    assert len(review_items) == 3
    assert all(len(item.payload['source_ids']) <= 2 for item in review_items)


def test_gmail_sync_runs_agent_only_for_changed_gmail_sources(client, db_session) -> None:
    _set_csrf_cookie(client)

    response = client.post('/api/v1/integrations/gmail/sync', headers=CSRF_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload['connector_type'] == 'gmail'
    assert payload['created_review_items'] == 1
    review_item = db_session.query(ReviewItem).one()
    assert review_item.payload['agent_name'] == 'mail_document_agent'
    assert all('.mock/project-alpha/redis-summary' in link for link in review_item.source_links)
    assert not any('drive.mock' in link for link in review_item.source_links)


def test_drive_sync_creates_review_item_per_changed_drive_source(client, db_session) -> None:
    _set_csrf_cookie(client)

    response = client.post('/api/v1/integrations/drive/sync', headers=CSRF_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload['connector_type'] == 'drive'
    assert payload['created_review_items'] == 2
    review_items = db_session.query(ReviewItem).order_by(ReviewItem.id).all()
    assert len(review_items) == 2
    assert all(item.payload['agent_name'] == 'mail_document_agent' for item in review_items)
    assert all(len(item.source_links) == 1 for item in review_items)
    assert all('drive.mock' in item.source_links[0] for item in review_items)
    assert not any('gmail.mock' in link for item in review_items for link in item.source_links)


def test_duplicate_gmail_sync_does_not_rerun_agent_for_unchanged_sources(client, db_session) -> None:
    _set_csrf_cookie(client)
    first_response = client.post('/api/v1/integrations/gmail/sync', headers=CSRF_HEADERS)
    assert first_response.status_code == 200
    assert first_response.json()['created_review_items'] == 1

    second_response = client.post('/api/v1/integrations/gmail/sync', headers=CSRF_HEADERS)

    assert second_response.status_code == 200
    assert second_response.json()['created_review_items'] == 0
    assert db_session.query(ReviewItem).count() == 1


def test_gmail_sync_smoke_ingests_attachment_metadata_boundary(client, db_session) -> None:
    _set_csrf_cookie(client)
    response = client.post('/api/v1/integrations/gmail/sync', headers=CSRF_HEADERS)

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
