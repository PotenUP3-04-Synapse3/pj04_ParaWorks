from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import sleep as default_sleep
from typing import Protocol

import httpx

from backend.app.connectors.base import ConnectorManifest, SourceEvent

SLACK_REQUIRED_SCOPES = (
    'channels:history',
    'groups:history',
    'im:history',
    'mpim:history',
    'channels:read',
    'groups:read',
    'im:read',
    'mpim:read',
    'users:read',
)


class SlackApiClient(Protocol):
    def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
        raise NotImplementedError

    def conversation_replies(self, channel_id: str, thread_ts: str, *, oldest: str | None = None) -> list[dict]:
        raise NotImplementedError

    def conversations_list(self) -> list[dict]:
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
        max_retries: int = 2,
        sleep: Callable[[float], None] = default_sleep,
    ) -> None:
        self.bot_token = bot_token
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.base_url = base_url.rstrip('/')
        self.page_limit = page_limit
        self.max_retries = max_retries
        self.sleep = sleep

    def conversation_history(self, channel_id: str, *, oldest: str | None = None) -> list[dict]:
        params = {
            'channel': channel_id,
            'limit': str(self.page_limit),
        }
        if oldest:
            params['oldest'] = oldest

        return self._get_paginated_items('conversations.history', 'messages', params)

    def conversation_replies(self, channel_id: str, thread_ts: str, *, oldest: str | None = None) -> list[dict]:
        params = {
            'channel': channel_id,
            'ts': thread_ts,
            'limit': str(self.page_limit),
        }
        if oldest:
            params['oldest'] = oldest

        return self._get_paginated_items('conversations.replies', 'messages', params)

    def conversations_list(self) -> list[dict]:
        return self._get_paginated_items(
            'conversations.list',
            'channels',
            {
                'types': 'public_channel,private_channel,im,mpim',
                'exclude_archived': 'true',
                'limit': str(self.page_limit),
            },
        )

    def users_list(self) -> list[dict]:
        return self._get_paginated_items('users.list', 'members', {'limit': str(self.page_limit)})

    def _get_paginated_items(self, method: str, item_key: str, params: dict[str, str]) -> list[dict]:
        items: list[dict] = []
        cursor: str | None = None

        while True:
            page_params = dict(params)
            if cursor:
                page_params['cursor'] = cursor

            response = self._get_with_retries(method, page_params)
            payload = response.json()
            if not payload.get('ok'):
                raise SlackApiError(f"Slack {method} failed: {payload.get('error', 'unknown_error')}")
            items.extend(payload.get(item_key, []))
            cursor = str(payload.get('response_metadata', {}).get('next_cursor') or '')
            if not cursor:
                break

        return items

    def _get_with_retries(self, method: str, params: dict[str, str]) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            response = self.http_client.get(
                f'{self.base_url}/{method}',
                headers={'Authorization': f'Bearer {self.bot_token}'},
                params=params,
            )
            if response.status_code == 429:
                if attempt >= self.max_retries:
                    raise SlackApiError(f'Slack {method} failed: rate_limited')
                self.sleep(_retry_after_seconds(response))
                continue
            if response.status_code >= 500:
                if attempt >= self.max_retries:
                    raise SlackApiError(f'Slack {method} failed: http_{response.status_code}')
                self.sleep(_retry_after_seconds(response))
                continue
            if response.status_code >= 400:
                raise SlackApiError(f'Slack {method} failed: http_{response.status_code}')
            return response
        raise SlackApiError(f'Slack {method} failed: retry_exhausted')


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
            required_scopes=SLACK_REQUIRED_SCOPES,
            sync_strategy='incremental',
            cost_policy='Fetch source deltas first; embed only changed chunks after review approval.',
        )

    def fetch_events(self) -> list[SourceEvent]:
        return self.fetch_events_since({})

    def fetch_events_since(self, latest_timestamps_by_partition: dict[str, str]) -> list[SourceEvent]:
        events: list[SourceEvent] = []
        
        # 설정된 채널 ID가 없으면 봇이 참여 중인 모든 채널을 자동으로 가져옴
        channel_ids = self.config.channel_ids
        if not channel_ids:
            all_channels = self.client.conversations_list()
            # public/private 채널은 is_member로 확인하고, DM(im/mpim)은 is_im/is_mpim으로 확인합니다.
            channel_ids = [
                c['id'] for c in all_channels 
                if c.get('is_member') or c.get('is_im') or c.get('is_mpim')
            ]
            
        for channel_id in channel_ids:
            oldest = latest_timestamps_by_partition.get(channel_id)
            for message in self.client.conversation_history(channel_id, oldest=oldest):
                if message.get('type') != 'message' or not message.get('text'):
                    continue
                events.append(self._message_to_source_event(channel_id, message))
                thread_ts = str(message.get('thread_ts') or message.get('ts') or '')
                if not thread_ts or int(message.get('reply_count') or 0) <= 0:
                    continue
                reply_index = 0
                parent_text = str(message.get('text') or '')
                for reply in self.client.conversation_replies(channel_id, thread_ts, oldest=oldest):
                    if reply.get('ts') == message.get('ts'):
                        continue
                    if reply.get('type') != 'message' or not reply.get('text'):
                        continue
                    reply_index += 1
                    events.append(
                        self._message_to_source_event(
                            channel_id,
                            reply,
                            parent_ts=thread_ts,
                            parent_text=parent_text,
                            reply_index=reply_index,
                        )
                    )
        return events

    def _message_to_source_event(
        self,
        channel_id: str,
        message: dict,
        *,
        parent_ts: str | None = None,
        parent_text: str | None = None,
        reply_index: int | None = None,
    ) -> SourceEvent:
        timestamp = str(message['ts'])
        author = message.get('user') or message.get('username')
        thread_ts = str(message.get('thread_ts') or parent_ts or timestamp)
        is_thread_reply = parent_ts is not None and timestamp != parent_ts
        reply_count = int(message.get('reply_count') or 0)
        body = _thread_context_body(message_text=str(message['text']), parent_text=parent_text)
        return SourceEvent(
            source_type='slack',
            source_id=f'{channel_id}:{timestamp}',
            source_url=_slack_permalink(self.config.workspace_url, channel_id, timestamp),
            title=f'Slack thread reply in {channel_id}' if is_thread_reply else f'Slack message in {channel_id}',
            body=body,
            author=author,
            participants=[author] if author else [],
            timestamp=datetime.fromtimestamp(float(timestamp), tz=UTC),
            permission_level='internal',
            raw_metadata={
                'channel_id': channel_id,
                'ts': timestamp,
                'thread_ts': thread_ts,
                'is_thread_parent': reply_count > 0 and thread_ts == timestamp,
                'is_thread_reply': is_thread_reply,
                'reply_count': reply_count,
                'thread_parent_text': parent_text,
                'thread_reply_index': reply_index,
                'thread_context_window': 'parent_plus_reply' if parent_text else 'single_message',
                'required_scopes': list(SLACK_REQUIRED_SCOPES),
            },
        )


def _slack_permalink(workspace_url: str, channel_id: str, timestamp: str) -> str:
    normalized_workspace = workspace_url.rstrip('/')
    permalink_ts = timestamp.replace('.', '').ljust(16, '0')
    return f'{normalized_workspace}/archives/{channel_id}/p{permalink_ts}'


def _thread_context_body(*, message_text: str, parent_text: str | None) -> str:
    if not parent_text:
        return message_text
    return f'Thread parent: {parent_text}\nThread reply: {message_text}'


def _retry_after_seconds(response: httpx.Response) -> float:
    try:
        return max(float(response.headers.get('Retry-After', '1')), 0.0)
    except ValueError:
        return 1.0
