def test_login_accepts_admin_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['email'] == 'admin@paraworks.com'
    assert payload['user']['role'] == 'admin'
    assert 'restricted' in payload['user']['permission_levels']


def test_login_accepts_employee_dummy_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'mina@paraworks.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['role'] == 'employee'
    assert payload['user']['department'] == 'Product'
    assert 'internal' in payload['user']['permission_levels']


def test_admin_can_list_demo_users(client) -> None:
    response = client.get('/api/v1/auth/users', headers={'X-Demo-User': 'admin'})

    assert response.status_code == 200
    payload = response.json()
    emails = {user['email'] for user in payload['users']}
    assert 'admin@paraworks.com' in emails
    assert {'mina@paraworks.com', 'jun@paraworks.com', 'soyeon@paraworks.com'} <= emails


def test_employee_cannot_list_demo_users(client) -> None:
    response = client.get('/api/v1/auth/users', headers={'X-Demo-User': 'viewer'})

    assert response.status_code == 403


def test_login_options_expose_sanitized_demo_users(client) -> None:
    response = client.get('/api/v1/auth/login-options')

    assert response.status_code == 200
    payload = response.json()
    assert all('permission_levels' in user for user in payload['users'])
    assert {user['email'] for user in payload['users']} >= {
        'admin@paraworks.com',
        'mina@paraworks.com',
    }
