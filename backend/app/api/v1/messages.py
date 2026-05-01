from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
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


def require_channel(db: Session, channel_id: str) -> dict:
    channel = get_channel(db, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail='message channel not found')
    return channel


@router.get('/channels', response_model=MessageChannelsResponse)
def get_message_channels(db: Session = Depends(get_db)) -> dict:
    return {'channels': list_channels(db)}


@router.get('/channels/{channel_id}/messages', response_model=ChannelMessagesResponse)
def get_channel_messages(channel_id: str, db: Session = Depends(get_db)) -> dict:
    channel = require_channel(db, channel_id)
    return {'channel': channel, 'messages': list_messages(db, channel_id)}


@router.post('/channels/{channel_id}/messages', response_model=MessageResponse)
def create_channel_message(
    channel_id: str,
    request: MessageCreateRequest,
    db: Session = Depends(get_db),
    user: DemoUser = Depends(get_demo_user),
) -> dict:
    require_channel(db, channel_id)
    return append_message(db, channel_id, request.body, user)
