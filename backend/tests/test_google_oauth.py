from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.connectors.google_oauth import (
    GoogleOAuthAccess,
    GoogleOAuthStateSigner,
    LocalTokenVault,
    build_google_oauth_install_url,
    complete_google_oauth_callback,
)
from backend.app.core.config import Settings, get_settings
from backend.app.models import IntegrationConnection


def test_google_oauth_install_url_contains_signed_state_and_hides_secret() -> None:
    settings = Settings(
        google_client_id='G123',
        google_client_secret='google-secret',
        google_oauth_redirect_uri='http://localhost:3000/integrations/google/callback',
        google_oauth_state_secret='google-state-secret',
    )

    install = build_google_oauth_install_url(settings=settings, connector_type='gmail', nonce='nonce-1')
    parsed = urlparse(install.install_url)
    params = parse_qs(parsed.query)

    assert parsed.netloc == 'accounts.google.com'
    assert parsed.path == '/o/oauth2/v2/auth'
    assert params['client_id'] == ['G123']
    assert params['redirect_uri'] == ['http://localhost:3000/integrations/google/callback']
    assert params['response_type'] == ['code']
    assert params['access_type'] == ['offline']
    assert params['prompt'] == ['consent']
    assert 'https://www.googleapis.com/auth/gmail.readonly' in params['scope'][0]
    assert 'google-secret' not in install.install_url
    assert install.state == params['state'][0]

    state = GoogleOAuthStateSigner('google-state-secret').validate(install.state)
    assert state.connector_type == 'gmail'
    assert state.nonce == 'nonce-1'


def test_complete_google_oauth_callback_persists_connection_without_raw_token(
    db_session: Session,
) -> None:
    settings = Settings(
        google_client_id='G123',
        google_client_secret='google-secret',
        google_oauth_redirect_uri='http://localhost:3000/integrations/google/callback',
        google_oauth_state_secret='google-state-secret',
    )
    state = GoogleOAuthStateSigner('google-state-secret').create(connector_type='drive', nonce='nonce-1')
    vault = LocalTokenVault()
    access = GoogleOAuthAccess(
        access_token='ya29.access-token',
        refresh_token='1//refresh-token',
        account_id='google-user-123',
        account_name='para@example.com',
        scopes=['https://www.googleapis.com/auth/drive.readonly'],
    )

    connection = complete_google_oauth_callback(
        db=db_session,
        settings=settings,
        connector_type='drive',
        code='temporary-code',
        state=state,
        access=access,
        token_vault=vault,
    )

    stored = db_session.query(IntegrationConnection).one()
    assert connection.id == stored.id
    assert stored.connector_type == 'drive'
    assert stored.workspace_id == 'google-user-123'
    assert stored.workspace_name == 'para@example.com'
    assert stored.workspace_url == 'https://workspace.google.com'
    assert stored.status == 'connected'
    assert stored.token_ref == 'local:drive:google-user-123:oauth'
    assert stored.masked_bot_token == '1//r...oken'
    assert vault.resolve('local:drive:google-user-123:oauth') == '1//refresh-token'
    assert 'ya29.access-token' not in str(stored.raw_metadata)
    assert '1//refresh-token' not in str(stored.raw_metadata)


def test_google_oauth_install_url_api_uses_settings_without_exposing_secret(
    client: TestClient,
) -> None:
    def override_settings() -> Settings:
        return Settings(
            google_client_id='G123',
            google_client_secret='google-secret',
            google_oauth_redirect_uri='http://localhost:3000/integrations/google/callback',
            google_oauth_state_secret='google-state-secret',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/integrations/gmail/oauth/install-url')

    assert response.status_code == 200
    payload = response.json()
    assert payload['configured'] is True
    assert payload['connector_type'] == 'gmail'
    assert 'https://www.googleapis.com/auth/gmail.readonly' in payload['required_scopes']
    assert 'google-secret' not in str(payload)


def test_google_oauth_install_url_api_fails_soft_when_unconfigured(client: TestClient) -> None:
    def override_settings() -> Settings:
        return Settings(google_client_id=None)

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/integrations/drive/oauth/install-url')

    assert response.status_code == 200
    assert response.json() == {
        'connector_type': 'drive',
        'configured': False,
        'install_url': None,
        'state': None,
        'required_scopes': [],
    }


def test_google_oauth_callback_api_rejects_connector_mismatch(client: TestClient) -> None:
    def override_settings() -> Settings:
        return Settings(
            google_client_id='G123',
            google_client_secret='google-secret',
            google_oauth_state_secret='google-state-secret',
        )

    client.app.dependency_overrides[get_settings] = override_settings
    state = GoogleOAuthStateSigner('google-state-secret').create(connector_type='gmail', nonce='nonce-1')

    response = client.get(
        '/api/v1/integrations/drive/oauth/callback',
        params={'code': 'temporary-code', 'state': state},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Google OAuth state connector mismatch'
