def test_viewer_search_cannot_see_restricted_drive_content(client) -> None:
    client.post('/api/v1/integrations/drive/sync')
    response = client.post('/api/v1/search', headers={'X-Demo-User': 'viewer'}, json={'query': 'confidential pricing'})
    assert response.status_code == 200
    assert response.json()['results'] == []
    assert response.json()['permission_notice'] == 'Some sources may be hidden by permissions.'


def test_admin_search_can_see_restricted_drive_content(client) -> None:
    client.post('/api/v1/integrations/drive/sync')
    response = client.post('/api/v1/search', headers={'X-Demo-User': 'admin'}, json={'query': 'confidential pricing'})
    assert response.status_code == 200
    assert len(response.json()['results']) == 1
