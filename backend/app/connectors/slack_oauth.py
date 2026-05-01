import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from backend.app.connectors.slack import SLACK_REQUIRED_HISTORY_SCOPES, SlackApiError
from backend.app.core.config import Settings
from backend.app.models import IntegrationConnection

SLACK_OAUTH_BOT_SCOPES = (
    *SLACK_REQUIRED_HISTORY_SCOPES,
    'channels:read',
    'groups:read',
    'users:read',
)


@dataclass(frozen=True)
class SlackOAuthState:
    connector_type: str
    nonce: str


@dataclass(frozen=True)
class SlackOAuthInstallUrl:
    connector_type: str
    install_url: str
    state: str
    required_scopes: list[str]
    configured: bool


@dataclass(frozen=True)
class SlackOAuthAccess:
    bot_token: str
    bot_user_id: str | None
    team_id: str
    team_name: str
    scopes: list[str]


class SlackOAuthConfigurationError(RuntimeError):
    pass


class SlackOAuthStateSigner:
    def __init__(self, secret: str) -> None:
        self.secret = secret.encode()

    def create(self, *, nonce: str | None = None, connector_type: str = 'slack') -> str:
        payload = {
            'connector_type': connector_type,
            'nonce': nonce or secrets.token_urlsafe(18),
        }
        payload_token = _b64encode(json.dumps(payload, separators=(',', ':')).encode())
        signature = _sign(payload_token, self.secret)
        return f'{payload_token}.{signature}'

    def validate(self, state: str) -> SlackOAuthState:
        try:
            payload_token, signature = state.split('.', 1)
        except ValueError as exc:
            raise SlackApiError('Slack OAuth state is malformed') from exc

        expected = _sign(payload_token, self.secret)
        if not hmac.compare_digest(signature, expected):
            raise SlackApiError('Slack OAuth state signature is invalid')

        payload = json.loads(_b64decode(payload_token))
        return SlackOAuthState(
            connector_type=str(payload['connector_type']),
            nonce=str(payload['nonce']),
        )


class SlackOAuthClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        http_client: httpx.Client | None = None,
        base_url: str = 'https://slack.com/api',
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.base_url = base_url.rstrip('/')

    def exchange_code(self, *, code: str, redirect_uri: str) -> SlackOAuthAccess:
        response = self.http_client.post(
            f'{self.base_url}/oauth.v2.access',
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get('ok'):
            raise SlackApiError(f"Slack oauth.v2.access failed: {payload.get('error', 'unknown_error')}")

        team = payload.get('team') or {}
        return SlackOAuthAccess(
            bot_token=str(payload['access_token']),
            bot_user_id=payload.get('bot_user_id'),
            team_id=str(team.get('id') or payload.get('team_id')),
            team_name=str(team.get('name') or 'Slack workspace'),
            scopes=_parse_scope_string(str(payload.get('scope') or '')),
        )


class LocalTokenVault:
    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def store_bot_token(self, *, connector_type: str, workspace_id: str, token: str) -> str:
        token_ref = f'local:{connector_type}:{workspace_id}:bot'
        self._secrets[token_ref] = token
        return token_ref

    def resolve(self, token_ref: str) -> str | None:
        return self._secrets.get(token_ref)


LOCAL_TOKEN_VAULT = LocalTokenVault()


def build_slack_oauth_install_url(
    *,
    settings: Settings,
    nonce: str | None = None,
) -> SlackOAuthInstallUrl:
    if not settings.slack_client_id:
        raise SlackOAuthConfigurationError('SLACK_CLIENT_ID is required for Slack OAuth install URL')

    state = SlackOAuthStateSigner(settings.slack_oauth_state_secret).create(nonce=nonce)
    query = urlencode(
        {
            'client_id': settings.slack_client_id,
            'scope': ','.join(SLACK_OAUTH_BOT_SCOPES),
            'redirect_uri': settings.slack_oauth_redirect_uri,
            'state': state,
        }
    )
    return SlackOAuthInstallUrl(
        connector_type='slack',
        install_url=f'https://slack.com/oauth/v2/authorize?{query}',
        state=state,
        required_scopes=list(SLACK_OAUTH_BOT_SCOPES),
        configured=True,
    )


def complete_slack_oauth_callback(
    *,
    db: Session,
    settings: Settings,
    code: str,
    state: str,
    access: SlackOAuthAccess | None = None,
    token_vault: LocalTokenVault = LOCAL_TOKEN_VAULT,
) -> IntegrationConnection:
    parsed_state = SlackOAuthStateSigner(settings.slack_oauth_state_secret).validate(state)
    if parsed_state.connector_type != 'slack':
        raise SlackApiError('Slack OAuth state connector mismatch')

    access_payload = access or _exchange_slack_code(settings=settings, code=code)
    token_ref = token_vault.store_bot_token(
        connector_type='slack',
        workspace_id=access_payload.team_id,
        token=access_payload.bot_token,
    )

    connection = (
        db.query(IntegrationConnection)
        .filter(
            IntegrationConnection.connector_type == 'slack',
            IntegrationConnection.workspace_id == access_payload.team_id,
        )
        .one_or_none()
    )
    if connection is None:
        connection = IntegrationConnection(
            connector_type='slack',
            workspace_id=access_payload.team_id,
            workspace_name=access_payload.team_name,
            token_ref=token_ref,
            masked_bot_token=mask_secret(access_payload.bot_token),
        )
        db.add(connection)

    connection.workspace_name = access_payload.team_name
    connection.workspace_url = settings.slack_workspace_url
    connection.bot_user_id = access_payload.bot_user_id
    connection.scopes = access_payload.scopes
    connection.token_ref = token_ref
    connection.masked_bot_token = mask_secret(access_payload.bot_token)
    connection.status = 'connected'
    connection.raw_metadata = {
        'state_nonce': parsed_state.nonce,
        'scope_count': len(access_payload.scopes),
    }

    db.commit()
    db.refresh(connection)
    return connection


def mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return '****'
    return f'{secret[:4]}...{secret[-4:]}'


def _exchange_slack_code(*, settings: Settings, code: str) -> SlackOAuthAccess:
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise SlackOAuthConfigurationError('Slack OAuth client id and secret are required for callback exchange')
    return SlackOAuthClient(
        client_id=settings.slack_client_id,
        client_secret=settings.slack_client_secret,
    ).exchange_code(code=code, redirect_uri=settings.slack_oauth_redirect_uri)


def _parse_scope_string(scope: str) -> list[str]:
    return [item.strip() for item in scope.split(',') if item.strip()]


def _sign(payload_token: str, secret: bytes) -> str:
    digest = hmac.new(secret, payload_token.encode(), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def _b64decode(value: str) -> bytes:
    padded = value + ('=' * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode())
