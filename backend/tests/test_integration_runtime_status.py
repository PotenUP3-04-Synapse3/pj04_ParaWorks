from backend.app.models import SyncJob


def test_slack_runtime_status_reports_mode_channels_and_latest_sync(client, db_session) -> None:
    db_session.add(
        SyncJob(
            job_id='slack-runtime-1',
            connector_type='slack',
            status='complete',
            message='fetched=12 created_review_items=2 skipped_events=10',
            progress_pct=100,
        )
    )
    db_session.commit()

    response = client.get('/api/v1/integrations/slack/runtime-status')

    assert response.status_code == 200
    payload = response.json()
    assert payload['connector_type'] == 'slack'
    assert payload['mode'] == 'mock'
    assert isinstance(payload['configured_channel_ids'], list)
    assert payload['connection_status'] == 'disconnected'
    assert payload['credential_status'] == 'missing'
    assert payload['latest_sync'] == {
        'job_id': 'slack-runtime-1',
        'status': 'complete',
        'message': 'fetched=12 created_review_items=2 skipped_events=10',
        'progress_pct': 100,
    }
    assert payload['cost_policy'] == {
        'status_lookup_triggers_sync': False,
        'status_lookup_triggers_llm': False,
    }


def test_google_runtime_status_reports_account_readiness_and_latest_sync(client, db_session) -> None:
    db_session.add(
        SyncJob(
            job_id='gmail-runtime-1',
            connector_type='gmail',
            status='failed',
            message='failed: missing scope',
            progress_pct=100,
        )
    )
    db_session.commit()

    response = client.get('/api/v1/integrations/gmail/runtime-status')

    assert response.status_code == 200
    payload = response.json()
    assert payload['connector_type'] == 'gmail'
    assert payload['mode'] == 'mock'
    assert payload['connection_status'] == 'disconnected'
    assert payload['credential_status'] == 'missing'
    assert payload['account_name'] is None
    assert payload['latest_sync'] == {
        'job_id': 'gmail-runtime-1',
        'status': 'failed',
        'message': 'failed: missing scope',
        'progress_pct': 100,
    }
    assert payload['cost_policy'] == {
        'status_lookup_triggers_sync': False,
        'status_lookup_triggers_llm': False,
    }


def test_google_runtime_status_rejects_unknown_connector(client) -> None:
    response = client.get('/api/v1/integrations/not-google/runtime-status')

    assert response.status_code == 404
    assert response.json()['detail'] == 'Connector not found'


def test_runtime_status_redacts_secret_like_sync_messages(client, db_session) -> None:
    db_session.add(
        SyncJob(
            job_id='slack-secret-runtime-1',
            connector_type='slack',
            status='failed',
            message='failed with xoxb-123456789012-secret-token token_ref=local:slack:T1:bot',
            progress_pct=100,
        )
    )
    db_session.commit()

    response = client.get('/api/v1/integrations/slack/runtime-status')

    assert response.status_code == 200
    message = response.json()['latest_sync']['message']
    assert 'xoxb-123456789012-secret-token' not in message
    assert 'local:slack:T1:bot' not in message
    assert message == 'failed with [redacted-secret] token_ref=[redacted-secret]'


def test_google_runtime_status_redacts_refresh_token_sync_messages(client, db_session) -> None:
    db_session.add(
        SyncJob(
            job_id='gmail-secret-runtime-1',
            connector_type='gmail',
            status='failed',
            message='refresh_token=1//refresh-secret client_secret=google-client-secret',
            progress_pct=100,
        )
    )
    db_session.commit()

    response = client.get('/api/v1/integrations/gmail/runtime-status')

    assert response.status_code == 200
    message = response.json()['latest_sync']['message']
    assert '1//refresh-secret' not in message
    assert 'google-client-secret' not in message
    assert message == 'refresh_token=[redacted-secret] client_secret=[redacted-secret]'
