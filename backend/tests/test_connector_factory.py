from sqlalchemy.orm import Session

from backend.app.connectors.factory import get_configured_connector, get_sync_connector
from backend.app.connectors.google import GoogleConnector, GoogleWebApiClient
from backend.app.connectors.mock import MockConnector
from backend.app.connectors.slack import SlackConnector, SlackWebApiClient
from backend.app.connectors.slack_oauth import LocalTokenVault
from backend.app.core.config import Settings
from backend.app.models import IntegrationConnection


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


def test_sync_connector_uses_installed_slack_connection_token_from_vault(
    db_session: Session,
) -> None:
    token_vault = LocalTokenVault()
    token_vault.store_bot_token(
        connector_type='slack',
        workspace_id='T123',
        token='xoxb-installed',
    )
    db_session.add(
        IntegrationConnection(
            connector_type='slack',
            workspace_id='T123',
            workspace_name='ParaWorks',
            bot_user_id='U999',
            scopes=['channels:history'],
            token_ref='local:slack:T123:bot',
            masked_bot_token='xoxb...lled',
            status='connected',
        )
    )
    db_session.commit()

    connector = get_sync_connector(
        'slack',
        Settings(
            paraworks_demo_mode=False,
            slack_bot_token=None,
            slack_channel_ids=' C123 ',
            slack_workspace_url='https://example.slack.com',
        ),
        db=db_session,
        token_vault=token_vault,
    )

    assert isinstance(connector, SlackConnector)
    assert connector.config.bot_token == 'xoxb-installed'
    assert connector.config.channel_ids == ['C123']
    assert isinstance(connector.client, SlackWebApiClient)
    assert connector.client.bot_token == 'xoxb-installed'


def test_sync_connector_allows_slack_channel_override_for_selected_sync(
    db_session: Session,
) -> None:
    token_vault = LocalTokenVault()
    token_vault.store_bot_token(
        connector_type='slack',
        workspace_id='T123',
        token='xoxb-installed',
    )
    db_session.add(
        IntegrationConnection(
            connector_type='slack',
            workspace_id='T123',
            workspace_name='ParaWorks',
            bot_user_id='U999',
            scopes=['channels:history'],
            token_ref='local:slack:T123:bot',
            masked_bot_token='xoxb...lled',
            status='connected',
        )
    )
    db_session.commit()

    connector = get_sync_connector(
        'slack',
        Settings(
            paraworks_demo_mode=False,
            slack_bot_token=None,
            slack_channel_ids=' C123, C456 ',
        ),
        db=db_session,
        token_vault=token_vault,
        slack_channel_ids_override=['C456'],
    )

    assert isinstance(connector, SlackConnector)
    assert connector.config.channel_ids == ['C456']


def test_sync_connector_falls_back_to_mock_when_installed_token_is_not_in_vault(
    db_session: Session,
) -> None:
    db_session.add(
        IntegrationConnection(
            connector_type='slack',
            workspace_id='T123',
            workspace_name='ParaWorks',
            bot_user_id='U999',
            scopes=['channels:history'],
            token_ref='local:slack:T123:bot',
            masked_bot_token='xoxb...lled',
            status='connected',
        )
    )
    db_session.commit()

    connector = get_sync_connector(
        'slack',
        Settings(
            paraworks_demo_mode=False,
            slack_bot_token=None,
            slack_channel_ids='C123',
        ),
        db=db_session,
        token_vault=LocalTokenVault(),
    )

    assert isinstance(connector, MockConnector)
    assert connector.source_type == 'slack'


def test_sync_connector_uses_installed_google_connection_token_from_vault(
    db_session: Session,
) -> None:
    token_vault = LocalTokenVault()
    token_vault.store_token(
        connector_type='gmail',
        workspace_id='google-user-1',
        token='google-installed-token',
        token_kind='oauth',
    )
    db_session.add(
        IntegrationConnection(
            connector_type='gmail',
            workspace_id='google-user-1',
            workspace_name='para@example.com',
            scopes=['https://www.googleapis.com/auth/gmail.readonly'],
            token_ref='local:gmail:google-user-1:oauth',
            masked_bot_token='goog...oken',
            status='connected',
        )
    )
    db_session.commit()

    connector = get_sync_connector(
        'gmail',
        Settings(paraworks_demo_mode=False),
        db=db_session,
        token_vault=token_vault,
    )

    assert isinstance(connector, GoogleConnector)
    assert connector.config.connector_type == 'gmail'
    assert connector.config.oauth_token == 'google-installed-token'
    assert connector.config.account_id == 'google-user-1'
    assert connector.config.account_name == 'para@example.com'
    assert isinstance(connector.client, GoogleWebApiClient)
    assert connector.client.oauth_token == 'google-installed-token'


def test_sync_connector_keeps_google_mock_in_demo_mode_even_with_installed_connection(
    db_session: Session,
) -> None:
    token_vault = LocalTokenVault()
    token_vault.store_token(
        connector_type='drive',
        workspace_id='google-user-1',
        token='google-installed-token',
        token_kind='oauth',
    )
    db_session.add(
        IntegrationConnection(
            connector_type='drive',
            workspace_id='google-user-1',
            workspace_name='para@example.com',
            scopes=['https://www.googleapis.com/auth/drive.readonly'],
            token_ref='local:drive:google-user-1:oauth',
            masked_bot_token='goog...oken',
            status='connected',
        )
    )
    db_session.commit()

    connector = get_sync_connector(
        'drive',
        Settings(paraworks_demo_mode=True),
        db=db_session,
        token_vault=token_vault,
    )

    assert isinstance(connector, MockConnector)
    assert connector.source_type == 'drive'


def test_sync_connector_falls_back_to_mock_when_installed_google_token_is_not_in_vault(
    db_session: Session,
) -> None:
    db_session.add(
        IntegrationConnection(
            connector_type='calendar',
            workspace_id='google-user-1',
            workspace_name='para@example.com',
            scopes=['https://www.googleapis.com/auth/calendar.readonly'],
            token_ref='local:calendar:google-user-1:oauth',
            masked_bot_token='goog...oken',
            status='connected',
        )
    )
    db_session.commit()

    connector = get_sync_connector(
        'calendar',
        Settings(paraworks_demo_mode=False),
        db=db_session,
        token_vault=LocalTokenVault(),
    )

    assert isinstance(connector, MockConnector)
    assert connector.source_type == 'calendar'
