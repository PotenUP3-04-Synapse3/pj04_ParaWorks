def test_viewer_search_cannot_see_restricted_drive_content(client) -> None:
    client.post('/api/v1/integrations/drive/sync')
    response = client.post('/api/v1/search', headers={'X-Demo-User': 'viewer'}, json={'query': 'confidential pricing'})
    assert response.status_code == 200
    assert response.json()['results'] == []
    assert response.json()['permission_notice'] == 'Some sources may be hidden by permissions.'
    assert response.json()['hidden_match_count'] == 1


def test_admin_search_can_see_restricted_drive_content(client) -> None:
    client.post('/api/v1/integrations/drive/sync')
    response = client.post('/api/v1/search', headers={'X-Demo-User': 'admin'}, json={'query': 'confidential pricing'})
    assert response.status_code == 200
    assert len(response.json()['results']) == 1
    assert response.json()['results'][0]['source_id'] == 'drive-permission-leakage-case'
    assert response.json()['hidden_match_count'] == 0
