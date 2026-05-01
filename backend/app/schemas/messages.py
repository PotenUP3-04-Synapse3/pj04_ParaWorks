from pydantic import BaseModel, Field


class MessageChannelResponse(BaseModel):
    id: str
    name: str
    description: str
    unread_count: int = 0


class MessageResponse(BaseModel):
    id: str
    channel_id: str
    author_name: str
    author_role: str
    body: str
    created_at: str


class MessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageChannelsResponse(BaseModel):
    channels: list[MessageChannelResponse]


class ChannelMessagesResponse(BaseModel):
    channel: MessageChannelResponse
    messages: list[MessageResponse]
