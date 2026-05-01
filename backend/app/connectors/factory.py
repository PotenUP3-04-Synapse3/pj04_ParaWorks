from backend.app.connectors.base import Connector
from backend.app.connectors.mock import CONNECTOR_TYPES, get_mock_connector
from backend.app.connectors.slack import (
    SlackConnector,
    SlackConnectorConfig,
    SlackWebApiClient,
)
from backend.app.core.config import Settings


def get_configured_connector(connector_type: str, settings: Settings) -> Connector:
    if connector_type == 'slack' and settings.slack_bot_token and settings.slack_channel_ids.strip():
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


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]
