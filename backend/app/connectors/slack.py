from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from backend.app.connectors.base import ConnectorManifest, SourceEvent

SLACK_REQUIRED_HISTORY_SCOPES = (
    'channels:history',
    'groups:history',
    'im:history',
    'mpim:history',
)


class SlackApiClient(Protocol):
    def conversation_history(self, channel_id: str) -> list[dict]:
        raise NotImplementedError


@dataclass(frozen=True)
class SlackConnectorConfig:
    bot_token: str
    channel_ids: list[str]
    workspace_url: str = 'https://slack.com'


@dataclass(frozen=True)
class SlackConnector:
    config: SlackConnectorConfig
    client: SlackApiClient
    source_type: str = 'slack'

    @property
    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type='slack',
            display_name='Slack',
            mode='live',
            auth_type='oauth',
            required_scopes=SLACK_REQUIRED_HISTORY_SCOPES,
            sync_strategy='incremental',
            cost_policy='Fetch source deltas first; embed only changed chunks after review approval.',
        )

    def fetch_events(self) -> list[SourceEvent]:
        events: list[SourceEvent] = []
        for channel_id in self.config.channel_ids:
            for message in self.client.conversation_history(channel_id):
                if message.get('type') != 'message' or not message.get('text'):
                    continue
                events.append(self._message_to_source_event(channel_id, message))
        return events

    def _message_to_source_event(self, channel_id: str, message: dict) -> SourceEvent:
        timestamp = str(message['ts'])
        author = message.get('user') or message.get('username')
        return SourceEvent(
            source_type='slack',
            source_id=f'{channel_id}:{timestamp}',
            source_url=_slack_permalink(self.config.workspace_url, channel_id, timestamp),
            title=f'Slack message in {channel_id}',
            body=str(message['text']),
            author=author,
            participants=[author] if author else [],
            timestamp=datetime.fromtimestamp(float(timestamp), tz=UTC),
            permission_level='internal',
            raw_metadata={
                'channel_id': channel_id,
                'ts': timestamp,
                'required_scopes': list(SLACK_REQUIRED_HISTORY_SCOPES),
            },
        )


def _slack_permalink(workspace_url: str, channel_id: str, timestamp: str) -> str:
    normalized_workspace = workspace_url.rstrip('/')
    permalink_ts = timestamp.replace('.', '').ljust(16, '0')
    return f'{normalized_workspace}/archives/{channel_id}/p{permalink_ts}'
