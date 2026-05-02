from backend.app.models import ReviewItem, Source, SyncJob


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
    assert payload['selected_channel_ids'] == payload['configured_channel_ids']
    assert payload['channel_options'] == [
        {
            'id': channel_id,
            'name': channel_id,
            'is_selected': True,
            'is_configured': True,
        }
        for channel_id in payload['configured_channel_ids']
    ]
    assert payload['latest_sync_summary'] == {
        'fetched_events': 12,
        'created_review_items': 2,
        'skipped_events': 10,
    }
    assert payload['last_error'] is None
    assert payload['agent_bridge'] == {
        'slack_source_count': 0,
        'pending_review_count': 0,
        'ready_for_agent_test': False,
    }
    assert payload['cost_policy'] == {
        'status_lookup_triggers_sync': False,
        'status_lookup_triggers_llm': False,
        'thread_reply_fetch_is_incremental': True,
    }


def test_slack_runtime_status_reports_error_hint_and_agent_bridge(client, db_session) -> None:
    db_session.add_all(
        [
            Source(
                source_type='slack',
                source_id='C123:1777600800.000100',
                source_url='https://example.slack.com/archives/C123/p1777600800000100',
                title='Slack message in C123',
                permission_level='internal',
                raw_metadata={'channel_id': 'C123'},
            ),
            ReviewItem(
                item_type='decision',
                payload={'title': 'pgvector 도입'},
                source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
                source_snippets=['pgvector로 갑니다'],
                confidence_score=0.91,
                permission_level='internal',
                status='pending_review',
            ),
            SyncJob(
                job_id='slack-runtime-failed',
                connector_type='slack',
                status='failed',
                message='Slack conversations.history failed: not_in_channel',
                progress_pct=100,
            ),
        ]
    )
    db_session.commit()

    response = client.get('/api/v1/integrations/slack/runtime-status')

    assert response.status_code == 200
    payload = response.json()
    assert payload['last_error'] == {
        'code': 'not_in_channel',
        'message': 'Slack conversations.history failed: not_in_channel',
        'action_hint': 'Slack 앱을 선택한 채널에 추가한 뒤 다시 동기화하세요.',
    }
    assert payload['agent_bridge'] == {
        'slack_source_count': 1,
        'pending_review_count': 1,
        'ready_for_agent_test': True,
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
