from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.assistant.service import (
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    get_owned_conversation,
    list_conversations,
    list_messages,
    serialize_conversation,
    serialize_message,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.rag.search_store import build_pgvector_search_store
from backend.app.schemas.assistant import (
    AssistantConversationCreatedResponse,
    AssistantConversationCreateRequest,
    AssistantConversationsResponse,
    AssistantMessageCreateRequest,
    AssistantMessagesResponse,
    AssistantTurnResponse,
)

router = APIRouter(prefix='/assistant', tags=['assistant'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def require_conversation(db: Session, user: DemoUser, conversation_id: int):
    try:
        return get_owned_conversation(db, user, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='assistant conversation not found') from exc


@router.get('/conversations', response_model=AssistantConversationsResponse)
def list_assistant_conversations(db: DbSession, user: CurrentUser) -> dict:
    conversations = list_conversations(db, user)
    return {
        'conversations': [
            serialize_conversation(conversation) for conversation in conversations
        ]
    }


@router.post('/conversations', response_model=AssistantConversationCreatedResponse)
def create_assistant_conversation(
    request: AssistantConversationCreateRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    conversation = create_conversation(db, user, title=request.title)
    return {'conversation': serialize_conversation(conversation)}


@router.get(
    '/conversations/{conversation_id}/messages',
    response_model=AssistantMessagesResponse,
)
def list_assistant_messages(
    conversation_id: int,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    conversation = require_conversation(db, user, conversation_id)
    messages = list_messages(db, user, conversation.id)
    return {
        'conversation': serialize_conversation(conversation),
        'messages': [serialize_message(message) for message in messages],
    }


@router.post(
    '/conversations/{conversation_id}/messages',
    response_model=AssistantTurnResponse,
)
def create_assistant_message(
    conversation_id: int,
    request: AssistantMessageCreateRequest,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    conversation = require_conversation(db, user, conversation_id)
    try:
        user_message = append_user_message(db, user, conversation, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    messages = list_messages(db, user, conversation.id)
    contextual_question = build_contextual_question(
        conversation=conversation,
        messages=messages,
        new_message=user_message.content,
    )
    vector_store = build_pgvector_search_store(db=db, settings=settings)
    answer = answer_question_with_rag(
        db=db,
        user=user,
        question=contextual_question,
        vector_store=vector_store,
    )
    try:
        assistant_message = append_assistant_message(
            db,
            user,
            conversation,
            content=answer.answer,
            citations=answer.citations,
            source_ids=answer.source_ids,
            source_links=answer.source_links,
            source_snippets=answer.source_snippets,
            permission_level=answer.permission_level,
            hidden_match_count=answer.hidden_match_count,
            permission_notice=answer.permission_notice,
            agent_run_id=answer.agent_run_id,
            metadata={
                'agent_name': answer.agent_name,
                'prompt_version': answer.prompt_version,
                'question': answer.question,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        'conversation': serialize_conversation(conversation),
        'user_message': serialize_message(user_message),
        'assistant_message': serialize_message(assistant_message),
    }
