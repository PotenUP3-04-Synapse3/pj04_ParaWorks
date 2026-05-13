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


def test_login_issues_month_long_auth_cookies(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})

    assert response.status_code == 200
    set_cookie = response.headers['set-cookie']
    assert 'paraworks_session=' in set_cookie
    assert 'paraworks_refresh=' in set_cookie
    assert 'paraworks_csrf=' in set_cookie
    assert set_cookie.count('Max-Age=2592000') >= 3

def test_login_accepts_employee_dummy_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'mina@paraworks.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['role'] == 'reviewer'
    assert payload['user']['department'] == 'Product'
    assert payload['user']['avatar_url'] == '/profile/mina%40paraworks.com.png'
    assert 'internal' in payload['user']['permission_levels']


def test_login_options_include_requested_google_seed_accounts(client) -> None:
    response = client.get('/api/v1/auth/login-options')

    assert response.status_code == 200
    users_by_email = {user['email']: user for user in response.json()['users']}
    assert users_by_email['hanvv3@gmail.com']['role'] == 'admin'
    assert users_by_email['hanvv3@gmail.com']['avatar_url'] == '/profile/hanvv3%40gmail.com.jpg'
    assert 'restricted' in users_by_email['hanvv3@gmail.com']['permission_levels']
    assert users_by_email['kjw4work@gmail.com']['role'] == 'admin'
    assert users_by_email['kjw4work@gmail.com']['avatar_url'] == '/profile/kjw4work%40gmail.com.jpg'
    assert users_by_email['kjw4work@gmail.com']['title'] == 'COO'
    assert users_by_email['yonghee199702@gmail.com']['role'] == 'admin'
    assert users_by_email['yonghee199702@gmail.com']['avatar_url'] == '/profile/yonghee199702%40gmail.com.jpg'
    assert users_by_email['yonghee199702@gmail.com']['title'] == 'CTO'
    assert users_by_email['hanvv3@koreacu.ac.kr']['role'] == 'employee'
    assert users_by_email['hanvv3@koreacu.ac.kr']['avatar_url'] == '/profile/hanvv3%40koreacu.ac.kr.png'
    assert 'internal' in users_by_email['hanvv3@koreacu.ac.kr']['permission_levels']


def test_login_accepts_requested_admin_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'hanvv3@gmail.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['email'] == 'hanvv3@gmail.com'
    assert payload['user']['role'] == 'admin'
    assert payload['user']['avatar_url'] == '/profile/hanvv3%40gmail.com.jpg'


def test_login_accepts_requested_kim_jongwoo_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'kjw4work@gmail.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['id'] == 'kjw4work'
    assert payload['user']['email'] == 'kjw4work@gmail.com'
    assert payload['user']['role'] == 'admin'
    assert payload['user']['name'] == 'Kim Jongwoo'
    assert payload['user']['title'] == 'COO'
    assert payload['user']['department'] == 'platform'
    assert payload['user']['avatar_url'] == '/profile/kjw4work%40gmail.com.jpg'


def test_login_accepts_requested_kim_yonghee_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'yonghee199702@gmail.com'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['id'] == 'yonghee199702'
    assert payload['user']['email'] == 'yonghee199702@gmail.com'
    assert payload['user']['role'] == 'admin'
    assert payload['user']['name'] == 'Kim Yonghee'
    assert payload['user']['title'] == 'CTO'
    assert payload['user']['department'] == 'platform'
    assert payload['user']['avatar_url'] == '/profile/yonghee199702%40gmail.com.jpg'


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
        'kjw4work@gmail.com',
        'yonghee199702@gmail.com',
        'hanvv3@koreacu.ac.kr',
        'mina@paraworks.com',
    } <= emails
    assert 'jun@paraworks.com' not in emails
    assert 'soyeon@paraworks.com' not in emails


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


def test_local_production_like_mode_allows_seed_account_session_login(monkeypatch, db_session: Session) -> None:
    monkeypatch.setenv('PARAWORKS_DEMO_MODE', 'false')
    monkeypatch.setenv('PARAWORKS_ENV', 'local')
    get_settings.cache_clear()
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as production_client:
            login_response = production_client.post('/api/v1/auth/login', json={'email': 'admin@paraworks.com'})
            assert login_response.status_code == 200
            assert login_response.json()['user']['role'] == 'admin'
            assert 'paraworks_session=' in login_response.headers['set-cookie']

            me_response = production_client.get('/api/v1/auth/me')
            assert me_response.status_code == 200
            assert me_response.json()['user']['email'] == 'admin@paraworks.com'

            agent_runs_response = production_client.get('/api/v1/agent-runs')
            assert agent_runs_response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
