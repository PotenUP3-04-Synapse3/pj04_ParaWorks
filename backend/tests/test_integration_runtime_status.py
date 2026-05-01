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
