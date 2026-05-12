from urllib.parse import parse_qs, urlparse

from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.auth.google_identity import (
    GoogleIdentityAccess,
    GoogleIdentityStateSigner,
    build_google_identity_login_url,
    complete_google_identity_login,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.session_auth import issue_auth_cookies


def test_google_identity_login_url_uses_identity_scopes_and_account_picker(client: TestClient) -> None:
    def override_settings() -> Settings:
        return Settings(
            google_client_id='G123',
            google_client_secret='google-secret',
            google_identity_redirect_uri='http://localhost:3000/login/google/callback',
            google_identity_state_secret='identity-secret',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/auth/google/login-url')

    assert response.status_code == 200
    payload = response.json()
    parsed = urlparse(payload['login_url'])
    params = parse_qs(parsed.query)
    assert payload['configured'] is True
    assert payload['missing_config'] == []
    assert payload['redirect_uri'] == 'http://localhost:3000/login/google/callback'
    assert payload['required_scopes'] == ['openid', 'email', 'profile']
    assert params['prompt'] == ['select_account']
    assert params['scope'] == ['openid email profile']
    assert params['redirect_uri'] == ['http://localhost:3000/login/google/callback']
    assert 'google-secret' not in payload['login_url']


def test_google_identity_login_url_reports_missing_configuration(client: TestClient) -> None:
    def override_settings() -> Settings:
        return Settings(
            google_client_id='G123',
            google_client_secret=None,
            google_identity_redirect_uri='http://localhost:3000/login/google/callback',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/auth/google/login-url')

    assert response.status_code == 200
    assert response.json() == {
        'configured': False,
        'login_url': None,
        'state': None,
        'required_scopes': ['openid', 'email', 'profile'],
        'redirect_uri': 'http://localhost:3000/login/google/callback',
        'missing_config': ['GOOGLE_CLIENT_SECRET'],
    }


def test_google_identity_login_url_reports_all_missing_configuration(client: TestClient) -> None:
    def override_settings() -> Settings:
        return Settings(
            google_client_id=None,
            google_client_secret=None,
            google_identity_redirect_uri='',
            google_identity_state_secret='',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/auth/google/login-url')

    assert response.status_code == 200
    assert response.json()['configured'] is False
    assert response.json()['missing_config'] == [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_IDENTITY_REDIRECT_URI',
        'GOOGLE_IDENTITY_STATE_SECRET',
    ]


def test_google_identity_callback_accepts_seeded_admin_user(db_session: Session) -> None:
    settings = Settings(google_identity_state_secret='identity-secret')
    state = GoogleIdentityStateSigner('identity-secret').create(nonce='nonce-1')
    response = Response()

    auth_user = complete_google_identity_login(
        db=db_session,
        settings=settings,
        response=response,
        code='temporary-code',
        state=state,
        access=GoogleIdentityAccess(
            subject='google-sub-admin',
            email='hanvv3@gmail.com',
            email_verified=True,
            name='Hanvv Admin',
        ),
        cookie_issuer=issue_auth_cookies,
    )

    assert auth_user.email == 'hanvv3@gmail.com'
    assert auth_user.role == 'admin'
    assert auth_user.external_id == 'google-sub-admin'
    assert 'paraworks_session=' in response.headers['set-cookie']


def test_google_identity_callback_accepts_seeded_employee_user(db_session: Session) -> None:
    settings = Settings(google_identity_state_secret='identity-secret')
    state = GoogleIdentityStateSigner('identity-secret').create(nonce='nonce-1')

    auth_user = complete_google_identity_login(
        db=db_session,
        settings=settings,
        response=Response(),
        code='temporary-code',
        state=state,
        access=GoogleIdentityAccess(
            subject='google-sub-employee',
            email='hanvv3@koreacu.ac.kr',
            email_verified=True,
            name='Hanvv Employee',
        ),
        cookie_issuer=issue_auth_cookies,
    )

    assert auth_user.email == 'hanvv3@koreacu.ac.kr'
    assert auth_user.role == 'employee'


def test_google_identity_callback_accepts_new_seeded_admin_users(db_session: Session) -> None:
    settings = Settings(google_identity_state_secret='identity-secret')
    state = GoogleIdentityStateSigner('identity-secret').create(nonce='nonce-1')

    jongwoo = complete_google_identity_login(
        db=db_session,
        settings=settings,
        response=Response(),
        code='temporary-code',
        state=state,
        access=GoogleIdentityAccess(
            subject='google-sub-kjw',
            email='kjw4work@gmail.com',
            email_verified=True,
            name='Kim Jongwoo',
        ),
        cookie_issuer=issue_auth_cookies,
    )

    assert jongwoo.email == 'kjw4work@gmail.com'
    assert jongwoo.role == 'admin'
    assert jongwoo.title == 'COO'

    state = GoogleIdentityStateSigner('identity-secret').create(nonce='nonce-2')
    yonghee = complete_google_identity_login(
        db=db_session,
        settings=settings,
        response=Response(),
        code='temporary-code',
        state=state,
        access=GoogleIdentityAccess(
            subject='google-sub-yonghee',
            email='yonghee199702@gmail.com',
            email_verified=True,
            name='Kim Yonghee',
        ),
        cookie_issuer=issue_auth_cookies,
    )

    assert yonghee.email == 'yonghee199702@gmail.com'
    assert yonghee.role == 'admin'
    assert yonghee.title == 'CTO'


def test_google_identity_callback_rejects_unknown_email(db_session: Session) -> None:
    settings = Settings(google_identity_state_secret='identity-secret')
    state = GoogleIdentityStateSigner('identity-secret').create(nonce='nonce-1')

    try:
        complete_google_identity_login(
            db=db_session,
            settings=settings,
            response=Response(),
            code='temporary-code',
            state=state,
            access=GoogleIdentityAccess(
                subject='google-sub-unknown',
                email='unknown@example.com',
                email_verified=True,
                name='Unknown User',
            ),
            cookie_issuer=issue_auth_cookies,
        )
    except ValueError as exc:
        assert str(exc) == 'Google account is not invited to ParaWorks.'
    else:
        raise AssertionError('Expected unknown Google email to be rejected.')


def test_google_identity_callback_rejects_unverified_email(db_session: Session) -> None:
    settings = Settings(google_identity_state_secret='identity-secret')
    state = GoogleIdentityStateSigner('identity-secret').create(nonce='nonce-1')

    try:
        complete_google_identity_login(
            db=db_session,
            settings=settings,
            response=Response(),
            code='temporary-code',
            state=state,
            access=GoogleIdentityAccess(
                subject='google-sub-admin',
                email='hanvv3@gmail.com',
                email_verified=False,
                name='Hanvv Admin',
            ),
            cookie_issuer=issue_auth_cookies,
        )
    except ValueError as exc:
        assert str(exc) == 'Google email must be verified.'
    else:
        raise AssertionError('Expected unverified Google email to be rejected.')


def test_build_google_identity_login_url_can_validate_state() -> None:
    settings = Settings(google_client_id='G123', google_identity_state_secret='identity-secret')

    login_url = build_google_identity_login_url(settings=settings, nonce='nonce-1')

    state = GoogleIdentityStateSigner('identity-secret').validate(login_url.state)
    assert state.nonce == 'nonce-1'
