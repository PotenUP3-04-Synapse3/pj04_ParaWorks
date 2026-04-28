from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from backend.connectors.base import BaseConnector, RawDocument
from backend.core.config import settings

log = structlog.get_logger(__name__)

# 중요 이벤트 키워드 (의사결정/blocker/일정 등)
DECISION_KEYWORDS = [
    '결정', '확정', '승인', '합의', '결론', '최종', 'decided', 'approved', 'confirmed',
    'blocker', '블로커', '차단', '연기', '취소', '변경', '담당자',
]


def _has_decision_signal(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in DECISION_KEYWORDS)


class SlackConnector(BaseConnector):
    def __init__(self):
        self._client: AsyncWebClient | None = None

    async def authenticate(self) -> None:
        self._client = AsyncWebClient(token=settings.slack_bot_token)
        try:
            await self._client.auth_test()
            log.info('slack.authenticated')
        except SlackApiError as exc:
            log.error('slack.auth_failed', error=str(exc))
            raise

    def _client_or_raise(self) -> AsyncWebClient:
        if self._client is None:
            raise RuntimeError('Call authenticate() first')
        return self._client

    async def _get_allowed_channels(self) -> list[dict]:
        """수집 허용 채널 목록 반환.
        public 채널: 기본 허용
        private 채널: source_permissions 테이블의 admin_approved 플래그로 제어
        (실제 DB 조회는 상위 서비스 레이어에서 수행하고 여기서는 전체 채널 반환)
        """
        client = self._client_or_raise()
        channels = []
        cursor: str | None = None
        while True:
            resp = await client.conversations_list(
                types='public_channel,private_channel',
                limit=200,
                cursor=cursor,
            )
            channels.extend(resp['channels'])
            cursor = resp.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
        return channels

    async def fetch_recent(self, since: datetime | None = None) -> list[RawDocument]:
        client = self._client_or_raise()
        channels = await self._get_allowed_channels()
        oldest = str(since.timestamp()) if since else None

        docs: list[RawDocument] = []
        for ch in channels:
            ch_id = ch['id']
            ch_name = ch.get('name', ch_id)
            is_private = ch.get('is_private', False)

            try:
                cursor = None
                while True:
                    resp = await client.conversations_history(
                        channel=ch_id,
                        oldest=oldest,
                        limit=200,
                        cursor=cursor,
                    )
                    for msg in resp.get('messages', []):
                        if msg.get('subtype'):  # 시스템 메시지 제외
                            continue
                        text = msg.get('text', '')
                        ts = msg.get('ts', '')
                        thread_ts = msg.get('thread_ts')

                        # 스레드가 있으면 스레드 전체 수집
                        replies_count = msg.get('reply_count', 0)
                        thread_docs = []
                        if thread_ts and replies_count > 0:
                            thread_docs = await self._fetch_thread(client, ch_id, thread_ts)

                        doc = RawDocument(
                            source_type='slack',
                            source_id=f'{ch_id}_{ts}',
                            source_url=f'https://slack.com/archives/{ch_id}/p{ts.replace(".", "")}',
                            title=f'#{ch_name}',
                            raw_content=text,
                            mime_type='text/plain',
                            metadata={
                                'channel_id': ch_id,
                                'channel_name': ch_name,
                                'is_private': is_private,
                                'ts': ts,
                                'thread_ts': thread_ts,
                                'user': msg.get('user', ''),
                                'reactions': msg.get('reactions', []),
                                'mentions': self._extract_mentions(text),
                                'has_decision_signal': _has_decision_signal(text),
                                'thread_messages': [
                                    {'text': d.raw_content, 'user': d.metadata.get('user'), 'ts': d.metadata.get('ts')}
                                    for d in thread_docs
                                ],
                            },
                        )
                        docs.append(doc)

                    cursor = resp.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
            except SlackApiError as exc:
                log.warning('slack.channel_skip', channel=ch_name, error=str(exc))
                continue

        log.info('slack.fetched', count=len(docs))
        return docs

    async def _fetch_thread(self, client: AsyncWebClient, channel: str, thread_ts: str) -> list[RawDocument]:
        try:
            resp = await client.conversations_replies(channel=channel, ts=thread_ts)
            docs = []
            for msg in resp.get('messages', [])[1:]:  # 첫 메시지는 부모
                docs.append(RawDocument(
                    source_type='slack',
                    source_id=f"{channel}_{msg.get('ts', '')}",
                    source_url=None,
                    title=None,
                    raw_content=msg.get('text', ''),
                    mime_type='text/plain',
                    metadata={
                        'user': msg.get('user', ''),
                        'ts': msg.get('ts', ''),
                        'parent_ts': thread_ts,
                    },
                ))
            return docs
        except SlackApiError:
            return []

    @staticmethod
    def _extract_mentions(text: str) -> list[str]:
        import re
        return re.findall(r'<@([A-Z0-9]+)>', text)

    async def fetch_permissions(self, source_id: str) -> list[dict]:
        # Slack 채널 멤버 목록으로 대체
        ch_id = source_id.split('_')[0] if '_' in source_id else source_id
        client = self._client_or_raise()
        try:
            resp = await client.conversations_members(channel=ch_id)
            return [{'user_id': uid, 'role': 'member'} for uid in resp.get('members', [])]
        except SlackApiError:
            return []
