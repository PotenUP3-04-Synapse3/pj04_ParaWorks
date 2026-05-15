from sqlalchemy.orm import Session

from backend.app.connectors.base import Connector
from backend.app.connectors.google import (
    GOOGLE_CONNECTOR_TYPES,
    GoogleConnector,
    GoogleConnectorConfig,
    GoogleWebApiClient,
)
from backend.app.connectors.mock import CONNECTOR_TYPES, get_mock_connector
from backend.app.connectors.slack import (
    SlackConnector,
    SlackConnectorConfig,
    SlackWebApiClient,
)
from backend.app.connectors.slack_oauth import LOCAL_TOKEN_VAULT, LocalTokenVault
from backend.app.core.config import Settings
from backend.app.models import IntegrationConnection


class ConnectorNotConfiguredError(RuntimeError):
    pass


def get_configured_connector(connector_type: str, settings: Settings) -> Connector:
    if (
        connector_type == 'slack'
        and not settings.paraworks_demo_mode
        and settings.slack_bot_token
    ):
        channel_ids = _parse_csv(settings.slack_channel_ids)
        return SlackConnector(
            config=SlackConnectorConfig(
                bot_token=settings.slack_bot_token,
                channel_ids=channel_ids,
                workspace_url=settings.slack_workspace_url,
            ),
            client=SlackWebApiClient(bot_token=settings.slack_bot_token),
            user_client=(
                SlackWebApiClient(bot_token=settings.slack_user_token)
                if settings.slack_user_token
                else None
            ),
        )

    if not settings.paraworks_demo_mode:
        raise ConnectorNotConfiguredError(
            f'{connector_type} connector is not connected. Complete OAuth or configure credentials before syncing.'
        )

    if connector_type not in CONNECTOR_TYPES:
        raise ValueError(f'Unsupported connector: {connector_type}')
    return get_mock_connector(connector_type)


def get_sync_connector(
    connector_type: str,
    settings: Settings,
    *,
    db: Session | None = None,
    token_vault: LocalTokenVault = LOCAL_TOKEN_VAULT,
    slack_channel_ids_override: list[str] | None = None,
) -> Connector:
    # 데모 모드인 경우 무조건 Mock 커넥터 반환 (우선순위 1)
    if settings.paraworks_demo_mode:
        if connector_type.startswith('mock-'):
            connector_type = connector_type.replace('mock-', '')
        if connector_type in CONNECTOR_TYPES:
            return get_mock_connector(connector_type)

    # 실제 연동 확인 (설치된 커넥터)
    if connector_type == 'slack':
        installed_connector = _get_installed_slack_connector(
            settings=settings,
            db=db,
            token_vault=token_vault,
            channel_ids_override=slack_channel_ids_override,
        )
        if installed_connector is not None:
            return installed_connector
            
    # 설치된 커넥터가 없거나 토큰이 없는 경우 .env 폴백 (로컬 개발용)
    if (
        connector_type == 'slack'
        and settings.slack_bot_token
    ):
        return SlackConnector(
            config=SlackConnectorConfig(
                bot_token=settings.slack_bot_token,
                channel_ids=(
                    _clean_channel_ids(slack_channel_ids_override)
                    if slack_channel_ids_override is not None
                    else _parse_csv(settings.slack_channel_ids)
                ),
                workspace_url=settings.slack_workspace_url,
            ),
            client=SlackWebApiClient(bot_token=settings.slack_bot_token),
            user_client=(
                SlackWebApiClient(bot_token=settings.slack_user_token)
                if settings.slack_user_token
                else None
            ),
        )

    if connector_type in GOOGLE_CONNECTOR_TYPES:
        installed_connector = _get_installed_google_connector(
            connector_type=connector_type,
            db=db,
            token_vault=token_vault,
            settings=settings,
        )
        if installed_connector is not None:
            return installed_connector

    return get_configured_connector(connector_type, settings)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]


def _clean_channel_ids(channel_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for channel_id in channel_ids:
        normalized = channel_id.strip()
        if normalized and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    return cleaned


def _get_installed_slack_connector(
    *,
    settings: Settings,
    db: Session | None,
    token_vault: LocalTokenVault,
    channel_ids_override: list[str] | None = None,
) -> SlackConnector | None:
    if db is None:
        return None

    connection = (
        db.query(IntegrationConnection)
        .filter(
            IntegrationConnection.connector_type == 'slack',
            IntegrationConnection.status == 'connected',
        )
        .order_by(IntegrationConnection.updated_at.desc())
        .first()
    )
    if connection is None:
        return None

    bot_token = token_vault.resolve(connection.token_ref)
    if not bot_token:
        raise ConnectorNotConfiguredError(
            'slack connector credential is missing. Reconnect Slack before syncing.'
        )

    user_token = _resolve_installed_slack_user_token(
        connection=connection,
        token_vault=token_vault,
    )

    return SlackConnector(
        config=SlackConnectorConfig(
            bot_token=bot_token,
            channel_ids=(
                _clean_channel_ids(channel_ids_override)
                if channel_ids_override is not None
                else _parse_csv(settings.slack_channel_ids)
            ),
            workspace_url=connection.workspace_url or settings.slack_workspace_url,
        ),
        client=SlackWebApiClient(bot_token=bot_token),
        user_client=SlackWebApiClient(bot_token=user_token) if user_token else None,
    )


def _resolve_installed_slack_user_token(
    *,
    connection: IntegrationConnection,
    token_vault: LocalTokenVault,
) -> str | None:
    if not connection.raw_metadata.get('has_user_token'):
        return None
    user_token_ref = (
        connection.token_ref.rsplit(':', 1)[0] + ':user'
        if connection.token_ref.endswith(':bot')
        else f'local:slack:{connection.workspace_id}:user'
    )
    return token_vault.resolve(user_token_ref)


def _get_installed_google_connector(
    *,
    connector_type: str,
    db: Session | None,
    token_vault: LocalTokenVault,
    settings: Settings,
) -> GoogleConnector | None:
    if db is None:
        return None

    connection = (
        db.query(IntegrationConnection)
        .filter(
            IntegrationConnection.connector_type == connector_type,
            IntegrationConnection.status == 'connected',
        )
        .order_by(IntegrationConnection.updated_at.desc())
        .first()
    )
    if connection is None:
        return None

    oauth_token = token_vault.resolve(connection.token_ref)
    if not oauth_token:
        raise ConnectorNotConfiguredError(
            f'{connector_type} connector credential is missing. Reconnect Google before syncing.'
        )

    # kjw: If it's a refresh token, we MUST exchange it for an access token before sync.
    # Otherwise, Google APIs will reject "Bearer <refresh_token>" calls.
    if connection.raw_metadata.get('token_kind') == 'refresh_token':
        from backend.app.connectors.google_oauth import GoogleOAuthClient
        try:
            client = GoogleOAuthClient(
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
            access = client.refresh_access_token(refresh_token=oauth_token)
            oauth_token = access.access_token
        except Exception:
            # Fallback to stored token and let it fail normally in the connector
            pass

    return GoogleConnector(
        config=GoogleConnectorConfig(
            connector_type=connector_type,
            oauth_token=oauth_token,
            account_id=connection.workspace_id,
            account_name=connection.workspace_name,
        ),
        client=GoogleWebApiClient(oauth_token=oauth_token),
    )
