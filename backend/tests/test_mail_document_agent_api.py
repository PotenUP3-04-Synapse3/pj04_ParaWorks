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
