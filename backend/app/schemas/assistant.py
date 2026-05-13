from pydantic import BaseModel, Field


class AssistantConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class AssistantMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AssistantConversationResponse(BaseModel):
    id: int
    title: str
    summary: str | None
    created_at: str
    updated_at: str


class AssistantMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations: list
    source_ids: list
    source_links: list
    source_snippets: list
    permission_level: str | None
    hidden_match_count: int
    permission_notice: str | None
    agent_run_id: int | None
    metadata: dict
    created_at: str


class AssistantConversationsResponse(BaseModel):
    conversations: list[AssistantConversationResponse]


class AssistantConversationCreatedResponse(BaseModel):
    conversation: AssistantConversationResponse


class AssistantMessagesResponse(BaseModel):
    conversation: AssistantConversationResponse
    messages: list[AssistantMessageResponse]


class AssistantTurnResponse(BaseModel):
    conversation: AssistantConversationResponse
    user_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse


class AssistantEmailSendResponse(BaseModel):
    message: AssistantMessageResponse
    status: str
    gmail_message_id: str | None = None
