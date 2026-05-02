from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx

from backend.app.connectors.base import ConnectorManifest, SourceEvent

SLACK_REQUIRED_HISTORY_SCOPES = (
    'channels:history',
    'groups:history',
    'im:history',
    'mpim:history',
)


class SlackApiClient(Protocol):
    def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
        raise NotImplementedError


class SlackApiError(RuntimeError):
    pass


class SlackWebApiClient:
    def __init__(
        self,
        *,
        bot_token: str,
        http_client: httpx.Client | None = None,
        base_url: str = 'https://slack.com/api',
        page_limit: int = 200,
    ) -> None:
        self.bot_token = bot_token
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.base_url = base_url.rstrip('/')
        self.page_limit = page_limit

    def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
        messages: list[dict] = []
        cursor: str | None = None

        while True:
            payload = self._get_history_page(channel_id=channel_id, cursor=cursor, oldest=oldest)
            messages.extend(payload.get('messages', []))
            cursor = str(payload.get('response_metadata', {}).get('next_cursor') or '')
            if not cursor:
                break

        return messages

    def _get_history_page(self, *, channel_id: str, cursor: str | None, oldest: str | None) -> dict:
        params = {
            'channel': channel_id,
            'limit': str(self.page_limit),
        }
        if oldest:
            params['oldest'] = oldest
        if cursor:
            params['cursor'] = cursor

        response = self.http_client.get(
            f'{self.base_url}/conversations.history',
            headers={'Authorization': f'Bearer {self.bot_token}'},
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get('ok'):
            raise SlackApiError(f"Slack conversations.history failed: {payload.get('error', 'unknown_error')}")
        return payload


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
        return self.fetch_events_since({})

    def fetch_events_since(self, latest_timestamps_by_partition: dict[str, str]) -> list[SourceEvent]:
        events: list[SourceEvent] = []
        for channel_id in self.config.channel_ids:
            oldest = latest_timestamps_by_partition.get(channel_id)
            for message in self.client.conversation_history(channel_id, oldest=oldest):
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
