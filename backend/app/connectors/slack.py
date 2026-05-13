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

    def users_list(self) -> list[dict]:
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

    def auth_test(self) -> dict:
        response = self._get_with_retries('auth.test', {})
        payload = response.json()
        if not payload.get('ok'):
            raise SlackApiError(f"Slack auth.test failed: {payload.get('error', 'unknown_error')}")
        return payload

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
        
        # 1. 사용자 목록을 가져와 ID -> 실명 매핑 생성 (작성자 이름 및 본문 멘션 치환용)
        user_map: dict[str, str] = {}
        try:
            for member in self.client.users_list():
                uid = member.get('id')
                if not uid:
                    continue
                # 실명이 있으면 실명을, 없으면 표시 이름을 사용
                name = member.get('real_name') or member.get('profile', {}).get('real_name') or member.get('name')
                if name:
                    user_map[uid] = name
        except Exception:
            # 사용자 목록을 가져오지 못해도 동기화는 계속 진행
            pass

        # 2. 대상 채널 결정
        configured_channel_ids = self.config.channel_ids
        
        # 3. 봇이 참여 중인 채널 목록 조회 (필터링용)
        all_channels = self.client.conversations_list()
        joined_channel_ids = {
            c['id'] for c in all_channels 
            if c.get('is_member') or c.get('is_im') or c.get('is_mpim')
        }
        
        # 4. 설정된 채널 중 봇이 참여 중인 채널만 선별
        if configured_channel_ids:
            # .env에 채널이 설정되어 있다면, 그중 봇이 들어있는 채널만 처리
            target_channel_ids = [cid for idx, cid in enumerate(configured_channel_ids) if cid in joined_channel_ids]
        else:
            # .env에 채널 설정이 없다면, 봇이 들어있는 모든 채널 처리
            target_channel_ids = list(joined_channel_ids)
            
        for channel_id in target_channel_ids:
            # 7일 전 타임스탬프 계산
            seven_days_ago = (datetime.now(UTC) - timedelta(days=7)).timestamp()
            
            # DB 기록이 없으면 최근 7일치만, 있으면 기록된 시점 이후만 가져옴
            oldest_val = latest_timestamps_by_partition.get(channel_id)
            oldest = str(max(float(oldest_val), seven_days_ago)) if oldest_val else str(seven_days_ago)
            
            for message in self.client.conversation_history(channel_id, oldest=oldest):
                if message.get('type') != 'message' or not message.get('text'):
                    continue
                events.append(self._message_to_source_event(channel_id, message, user_map=user_map))
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
                            user_map=user_map,
                        )
                    )
        return events

    def _message_to_source_event(
        self,
        channel_id: str,
        message: dict,
        *,
        user_map: dict[str, str],
        parent_ts: str | None = None,
        parent_text: str | None = None,
        reply_index: int | None = None,
    ) -> SourceEvent:
        timestamp = str(message['ts'])
        user_id = message.get('user') or message.get('username')
        # 사용자 ID를 실명으로 변환
        author = user_map.get(user_id, user_id) if user_id else None
        
        thread_ts = str(message.get('thread_ts') or parent_ts or timestamp)
        is_thread_reply = parent_ts is not None and timestamp != parent_ts
        reply_count = int(message.get('reply_count') or 0)
        
        raw_text = str(message['text'])
        # 본문 내 사용자 멘션(<@U...>)을 실명으로 치환
        body_text = _resolve_mentions(raw_text, user_map)
        resolved_parent_text = _resolve_mentions(parent_text, user_map) if parent_text else None
        
        body = _thread_context_body(message_text=body_text, parent_text=resolved_parent_text)
        
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
                'thread_parent_text': resolved_parent_text,
                'thread_reply_index': reply_index,
                'thread_context_window': 'parent_plus_reply' if parent_text else 'single_message',
                'required_scopes': list(SLACK_REQUIRED_SCOPES),
                'slack_user_id': user_id,
            },
        )


def _slack_permalink(workspace_url: str, channel_id: str, timestamp: str) -> str:
    normalized_workspace = workspace_url.rstrip('/')
    permalink_ts = timestamp.replace('.', '').ljust(16, '0')
    return f'{normalized_workspace}/archives/{channel_id}/p{permalink_ts}'


def _resolve_mentions(text: str, user_map: dict[str, str]) -> str:
    """텍스트 내의 <@U...> 멘션을 실명으로 치환합니다."""
    if not text:
        return text
    import re
    def replace_mention(match):
        uid = match.group(1)
        return f"@{user_map.get(uid, uid)}"
    
    return re.sub(r'<@([A-Z0-9]+)>', replace_mention, text)


def _thread_context_body(*, message_text: str, parent_text: str | None) -> str:
    if not parent_text:
        return message_text
    return f'Thread parent: {parent_text}\nThread reply: {message_text}'


def _retry_after_seconds(response: httpx.Response) -> float:
    try:
        return max(float(response.headers.get('Retry-After', '1')), 0.0)
    except ValueError:
        return 1.0
