from sqlalchemy.orm import Session

from backend.app.connectors.base import Connector
from backend.app.connectors.mock import CONNECTOR_TYPES, get_mock_connector
from backend.app.connectors.slack import (
    SlackConnector,
    SlackConnectorConfig,
    SlackWebApiClient,
)
from backend.app.connectors.slack_oauth import LOCAL_TOKEN_VAULT, LocalTokenVault
from backend.app.core.config import Settings
from backend.app.models import IntegrationConnection


def get_configured_connector(connector_type: str, settings: Settings) -> Connector:
    if (
        connector_type == 'slack'
        and not settings.paraworks_demo_mode
        and settings.slack_bot_token
        and settings.slack_channel_ids.strip()
    ):
        channel_ids = _parse_csv(settings.slack_channel_ids)
        return SlackConnector(
            config=SlackConnectorConfig(
                bot_token=settings.slack_bot_token,
                channel_ids=channel_ids,
                workspace_url=settings.slack_workspace_url,
            ),
            client=SlackWebApiClient(bot_token=settings.slack_bot_token),
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
) -> Connector:
    if (
        connector_type == 'slack'
        and not settings.paraworks_demo_mode
        and settings.slack_channel_ids.strip()
    ):
        installed_connector = _get_installed_slack_connector(
            settings=settings,
            db=db,
            token_vault=token_vault,
        )
        if installed_connector is not None:
            return installed_connector

    return get_configured_connector(connector_type, settings)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]


def _get_installed_slack_connector(
    *,
    settings: Settings,
    db: Session | None,
    token_vault: LocalTokenVault,
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
        return None

    return SlackConnector(
        config=SlackConnectorConfig(
            bot_token=bot_token,
            channel_ids=_parse_csv(settings.slack_channel_ids),
            workspace_url=connection.workspace_url or settings.slack_workspace_url,
        ),
        client=SlackWebApiClient(bot_token=bot_token),
    )
