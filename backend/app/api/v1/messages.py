from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.messages.service import (
    append_message,
    get_channel,
    list_channels,
    list_messages,
)
from backend.app.schemas.messages import (
    ChannelMessagesResponse,
    MessageChannelsResponse,
    MessageCreateRequest,
    MessageResponse,
)

router = APIRouter(prefix='/messages', tags=['messages'])


def require_channel(channel_id: str) -> dict:
    channel = get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail='message channel not found')
    return channel


@router.get('/channels', response_model=MessageChannelsResponse)
def get_message_channels() -> dict:
    return {'channels': list_channels()}


@router.get('/channels/{channel_id}/messages', response_model=ChannelMessagesResponse)
def get_channel_messages(channel_id: str) -> dict:
    channel = require_channel(channel_id)
    return {'channel': channel, 'messages': list_messages(channel_id)}


@router.post('/channels/{channel_id}/messages', response_model=MessageResponse)
def create_channel_message(
    channel_id: str,
    request: MessageCreateRequest,
    user: DemoUser = Depends(get_demo_user),
) -> dict:
    require_channel(channel_id)
    return append_message(channel_id, request.body, user)
