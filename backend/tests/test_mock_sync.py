def test_mock_slack_sync_creates_pending_review_items(client) -> None:
    response = client.post('/api/v1/integrations/slack/sync')
    assert response.status_code == 200
    assert response.json()['status'] == 'complete'

    review_response = client.get('/api/v1/review?status=pending_review')
    assert review_response.status_code == 200
    assert review_response.json()['items']


def test_production_like_sync_requires_real_connection(monkeypatch, client) -> None:
    from backend.app.core.config import get_settings

    monkeypatch.setenv('PARAWORKS_DEMO_MODE', 'false')
    monkeypatch.setenv('SLACK_BOT_TOKEN', '')
    get_settings.cache_clear()
    login_response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})
    assert login_response.status_code == 200

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 409
    assert 'not connected' in response.json()['detail']
