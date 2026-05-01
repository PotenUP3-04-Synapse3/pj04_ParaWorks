from backend.app.connectors.factory import get_configured_connector
from backend.app.connectors.mock import MockConnector
from backend.app.connectors.slack import SlackConnector, SlackWebApiClient
from backend.app.core.config import Settings


def test_connector_factory_uses_mock_when_slack_credentials_are_missing() -> None:
    connector = get_configured_connector(
        'slack',
        Settings(slack_bot_token=None, slack_channel_ids=''),
    )

    assert isinstance(connector, MockConnector)
    assert connector.source_type == 'slack'


def test_connector_factory_keeps_mock_in_demo_mode_even_with_slack_credentials() -> None:
    connector = get_configured_connector(
        'slack',
        Settings(
            paraworks_demo_mode=True,
            slack_bot_token='xoxb-test',
            slack_channel_ids='C123',
        ),
    )

    assert isinstance(connector, MockConnector)
    assert connector.source_type == 'slack'


def test_connector_factory_builds_live_slack_connector_from_settings() -> None:
    connector = get_configured_connector(
        'slack',
        Settings(
            paraworks_demo_mode=False,
            slack_bot_token='xoxb-test',
            slack_channel_ids=' C123, C456 ',
            slack_workspace_url='https://example.slack.com',
        ),
    )

    assert isinstance(connector, SlackConnector)
    assert connector.config.channel_ids == ['C123', 'C456']
    assert connector.config.workspace_url == 'https://example.slack.com'
    assert isinstance(connector.client, SlackWebApiClient)
