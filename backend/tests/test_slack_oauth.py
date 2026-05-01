from urllib.parse import parse_qs, urlparse

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.connectors.slack_oauth import (
    LocalTokenVault,
    SlackOAuthAccess,
    SlackOAuthClient,
    SlackOAuthStateSigner,
    build_slack_oauth_install_url,
    complete_slack_oauth_callback,
)
from backend.app.core.config import Settings, get_settings
from backend.app.models import IntegrationConnection


def test_slack_oauth_install_url_contains_signed_state_and_hides_secret() -> None:
    settings = Settings(
        slack_client_id='C123',
        slack_client_secret='super-secret',
        slack_oauth_redirect_uri='http://localhost:3000/integrations/slack/callback',
        slack_oauth_state_secret='state-secret',
    )

    install = build_slack_oauth_install_url(settings=settings, nonce='nonce-1')
    parsed = urlparse(install.install_url)
    params = parse_qs(parsed.query)

    assert parsed.netloc == 'slack.com'
    assert parsed.path == '/oauth/v2/authorize'
    assert params['client_id'] == ['C123']
    assert params['redirect_uri'] == ['http://localhost:3000/integrations/slack/callback']
    assert 'channels:history' in params['scope'][0]
    assert 'groups:history' in params['scope'][0]
    assert 'super-secret' not in install.install_url
    assert install.state == params['state'][0]

    state = SlackOAuthStateSigner('state-secret').validate(install.state)
    assert state.connector_type == 'slack'
    assert state.nonce == 'nonce-1'


def test_slack_oauth_client_exchanges_code_for_access_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                'ok': True,
                'access_token': 'xoxb-secret-token',
                'bot_user_id': 'U999',
                'scope': 'channels:history,groups:history',
                'team': {'id': 'T123', 'name': 'ParaWorks'},
            },
        )

    client = SlackOAuthClient(
        client_id='C123',
        client_secret='client-secret',
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    access = client.exchange_code(
        code='temporary-code',
        redirect_uri='http://localhost:3000/integrations/slack/callback',
    )

    assert access.bot_token == 'xoxb-secret-token'
    assert access.team_id == 'T123'
    assert access.team_name == 'ParaWorks'
    body = requests[0].content.decode()
    assert 'client_id=C123' in body
    assert 'client_secret=client-secret' in body
    assert 'code=temporary-code' in body


def test_complete_slack_oauth_callback_persists_connection_without_raw_token(
    db_session: Session,
) -> None:
    settings = Settings(
        slack_client_id='C123',
        slack_client_secret='client-secret',
        slack_oauth_redirect_uri='http://localhost:3000/integrations/slack/callback',
        slack_oauth_state_secret='state-secret',
    )
    state = SlackOAuthStateSigner('state-secret').create(nonce='nonce-1')
    vault = LocalTokenVault()
    access = SlackOAuthAccess(
        bot_token='xoxb-secret-token',
        bot_user_id='U999',
        team_id='T123',
        team_name='ParaWorks',
        scopes=['channels:history', 'groups:history'],
    )

    connection = complete_slack_oauth_callback(
        db=db_session,
        settings=settings,
        code='temporary-code',
        state=state,
        access=access,
        token_vault=vault,
    )

    stored = db_session.query(IntegrationConnection).one()
    assert connection.id == stored.id
    assert stored.connector_type == 'slack'
    assert stored.workspace_id == 'T123'
    assert stored.workspace_name == 'ParaWorks'
    assert stored.status == 'connected'
    assert stored.token_ref == 'local:slack:T123:bot'
    assert stored.masked_bot_token == 'xoxb...oken'
    assert vault.resolve('local:slack:T123:bot') == 'xoxb-secret-token'
    assert 'xoxb-secret-token' not in str(stored.raw_metadata)


def test_slack_oauth_install_url_api_uses_settings_without_exposing_secret(
    client: TestClient,
) -> None:
    def override_settings() -> Settings:
        return Settings(
            slack_client_id='C123',
            slack_client_secret='client-secret',
            slack_oauth_redirect_uri='http://localhost:3000/integrations/slack/callback',
            slack_oauth_state_secret='state-secret',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get('/api/v1/integrations/slack/oauth/install-url')

    assert response.status_code == 200
    payload = response.json()
    assert payload['configured'] is True
    assert payload['connector_type'] == 'slack'
    assert 'channels:history' in payload['required_scopes']
    assert 'client-secret' not in str(payload)


def test_slack_oauth_callback_api_rejects_invalid_state(client: TestClient) -> None:
    def override_settings() -> Settings:
        return Settings(
            slack_client_id='C123',
            slack_client_secret='client-secret',
            slack_oauth_redirect_uri='http://localhost:3000/integrations/slack/callback',
            slack_oauth_state_secret='state-secret',
        )

    client.app.dependency_overrides[get_settings] = override_settings

    response = client.get(
        '/api/v1/integrations/slack/oauth/callback',
        params={'code': 'temporary-code', 'state': 'not-a-signed-state'},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Slack OAuth state is malformed'
