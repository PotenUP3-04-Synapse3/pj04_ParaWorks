"""Slack connector — OAuth and event handling."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def get_client(bot_token: str) -> WebClient:
    return WebClient(token=bot_token)


def get_thread_messages(
    bot_token: str, channel: str, thread_ts: str
) -> List[Dict]:
    """Fetch all messages in a Slack thread."""
    client = get_client(bot_token)
    try:
        response = client.conversations_replies(channel=channel, ts=thread_ts)
        return response.get('messages', [])
    except SlackApiError as e:
        logger.error('Failed to fetch Slack thread %s: %s', thread_ts, e)
        return []


def get_channel_history(
    bot_token: str,
    channel: str,
    oldest: Optional[str] = None,
    latest: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    """Fetch messages from a Slack channel."""
    client = get_client(bot_token)
    kwargs: Dict[str, Any] = {'channel': channel, 'limit': limit}
    if oldest:
        kwargs['oldest'] = oldest
    if latest:
        kwargs['latest'] = latest
    try:
        response = client.conversations_history(**kwargs)
        return response.get('messages', [])
    except SlackApiError as e:
        logger.error('Failed to fetch Slack history for %s: %s', channel, e)
        return []


def get_user_info(bot_token: str, user_id: str) -> Dict:
    client = get_client(bot_token)
    try:
        return client.users_info(user=user_id).get('user', {})
    except SlackApiError:
        return {}
