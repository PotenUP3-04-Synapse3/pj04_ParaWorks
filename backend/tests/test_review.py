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
