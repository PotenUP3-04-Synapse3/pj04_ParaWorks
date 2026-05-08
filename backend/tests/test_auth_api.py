from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import create_app


def test_login_accepts_admin_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['email'] == 'admin@paraworks.com'
    assert payload['user']['role'] == 'admin'
    assert payload['user']['avatar_url'] is None
    assert 'restricted' in payload['user']['permission_levels']
    assert 'paraworks_session=' in response.headers['set-cookie']
    assert 'paraworks_refresh=' in response.headers['set-cookie']
    assert 'HttpOnly' in response.headers['set-cookie']


def test_login_accepts_employee_dummy_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'mina@paraworks.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['role'] == 'reviewer'
    assert payload['user']['department'] == 'Product'
    assert payload['user']['avatar_url'] == '/profile/mina.png'
    assert 'internal' in payload['user']['permission_levels']


def test_login_options_include_requested_google_seed_accounts(client) -> None:
    response = client.get('/api/v1/auth/login-options')

    assert response.status_code == 200
    users_by_email = {user['email']: user for user in response.json()['users']}
    assert users_by_email['hanvv3@gmail.com']['role'] == 'admin'
    assert users_by_email['hanvv3@gmail.com']['avatar_url'] is None
    assert 'restricted' in users_by_email['hanvv3@gmail.com']['permission_levels']
    assert users_by_email['hanvv3@koreacu.ac.kr']['role'] == 'employee'
    assert users_by_email['hanvv3@koreacu.ac.kr']['avatar_url'] == '/profile/hanvv3.png'
    assert 'internal' in users_by_email['hanvv3@koreacu.ac.kr']['permission_levels']


def test_login_accepts_requested_admin_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'hanvv3@gmail.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['email'] == 'hanvv3@gmail.com'
    assert payload['user']['role'] == 'admin'


def test_login_accepts_requested_employee_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'hanvv3@koreacu.ac.kr'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['email'] == 'hanvv3@koreacu.ac.kr'
    assert payload['user']['role'] == 'employee'


def test_admin_can_list_demo_users(client) -> None:
    response = client.get('/api/v1/auth/users', headers={'X-Demo-User': 'admin'})

    assert response.status_code == 200
    payload = response.json()
    emails = {user['email'] for user in payload['users']}
    assert 'admin@paraworks.com' in emails
    assert {
        'hanvv3@gmail.com',
        'hanvv3@koreacu.ac.kr',
        'mina@paraworks.com',
        'jun@paraworks.com',
        'soyeon@paraworks.com',
    } <= emails


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


def test_me_prefers_http_only_session_cookie_over_demo_header(client) -> None:
    login_response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})
    assert login_response.status_code == 200

    response = client.get('/api/v1/auth/me', headers={'X-Demo-User': 'viewer'})

    assert response.status_code == 200
    assert response.json()['user']['email'] == 'admin@paraworks.com'
    assert response.json()['user']['avatar_url'] is None


def test_refresh_rotates_refresh_cookie(client) -> None:
    login_response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})
    original_refresh = login_response.cookies.get('paraworks_refresh')

    response = client.post('/api/v1/auth/refresh')

    assert response.status_code == 200
    assert response.json()['user']['email'] == 'admin@paraworks.com'
    assert response.cookies.get('paraworks_refresh') != original_refresh
    assert 'paraworks_session=' in response.headers['set-cookie']
    assert 'paraworks_refresh=' in response.headers['set-cookie']


def test_logout_revokes_cookie_session(client) -> None:
    login_response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})
    assert login_response.status_code == 200

    logout_response = client.post('/api/v1/auth/logout')

    assert logout_response.status_code == 200
    assert logout_response.json()['status'] == 'logged_out'
    assert 'paraworks_session=' in logout_response.headers['set-cookie']
    assert 'paraworks_refresh=' in logout_response.headers['set-cookie']


def test_production_mode_rejects_missing_session_cookie(monkeypatch, db_session: Session) -> None:
    monkeypatch.setenv('PARAWORKS_DEMO_MODE', 'false')
    get_settings.cache_clear()
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as production_client:
            response = production_client.get('/api/v1/auth/me')

        assert response.status_code == 401
        assert response.json()['detail'] == 'Authentication required.'
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
