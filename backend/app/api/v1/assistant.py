from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.assistant.email_actions import (
    EMAIL_ACTION_PROMPT_VERSION,
    assistant_email_draft_content,
    email_draft_metadata,
)
from backend.app.assistant.email_agent import (
    EmailActionDecision,
    build_email_action_agent,
    render_email_action_context,
)
from backend.app.assistant.gmail_sender import GmailDraftSender, GmailSendError
from backend.app.assistant.service import (
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    find_reusable_empty_conversation,
    get_owned_conversation,
    get_owned_message,
    list_conversations,
    list_messages,
    serialize_conversation,
    serialize_message,
    update_message_metadata,
)
from backend.app.assistant.tool_logging import AssistantToolLogger
from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.rag.search_store import build_pgvector_search_store
from backend.app.schemas.assistant import (
    AssistantConversationCreatedResponse,
    AssistantConversationCreateRequest,
    AssistantConversationsResponse,
    AssistantEmailSendResponse,
    AssistantMessageCreateRequest,
    AssistantMessagesResponse,
    AssistantTurnResponse,
)

router = APIRouter(prefix='/assistant', tags=['assistant'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]
ASSISTANT_FAILURE_CONTENT = '답변 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.'


def require_conversation(db: Session, user: DemoUser, conversation_id: int):
    try:
        return get_owned_conversation(db, user, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='assistant conversation not found') from exc


def append_failed_assistant_message(
    db: Session,
    user: DemoUser,
    conversation,
    *,
    reason: str,
    failure_class: str,
    agent_run_id: int | None = None,
):
    return append_assistant_message(
        db,
        user,
        conversation,
        content=ASSISTANT_FAILURE_CONTENT,
        citations=[],
        source_ids=[],
        source_links=[],
        source_snippets=[],
        permission_level=None,
        hidden_match_count=0,
        permission_notice=None,
        agent_run_id=agent_run_id,
        metadata={
            'status': 'failed',
            'failure_reason': reason,
            'failure_class': failure_class,
        },
    )


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
    if request.title is None or request.title.strip() == '새 대화':
        reusable_conversation = find_reusable_empty_conversation(db, user)
        if reusable_conversation is not None:
            return {'conversation': serialize_conversation(reusable_conversation)}

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
    tool_logger = AssistantToolLogger(settings.assistant_tool_log_path)
    tool_logger.log(
        'email_action_agent',
        f'start conversation_id={conversation.id} message_id={user_message.id}',
    )
    email_decision: EmailActionDecision = build_email_action_agent(settings).decide(
        conversation_context=render_email_action_context(
            messages=messages[:-1],
            max_chars=settings.assistant_email_agent_max_input_chars,
        ),
        latest_message=user_message.content,
    )
    tool_logger.log(
        'email_action_agent',
        (
            f'result action={email_decision.action_type} '
            f'confidence={email_decision.confidence_score:g} '
            f'model={email_decision.model_name or "deterministic"}'
        ),
    )
    confident_action = email_decision.confidence_score >= settings.assistant_email_agent_min_confidence
    email_draft = email_decision.to_draft() if confident_action else None
    if email_draft is not None:
        assistant_message = append_assistant_message(
            db,
            user,
            conversation,
            content=assistant_email_draft_content(email_draft),
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level=None,
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={
                **email_draft_metadata(email_draft),
                'agent_name': 'email_action_agent',
                'model_name': email_decision.model_name,
                'confidence_score': email_decision.confidence_score,
            },
        )
        return {
            'conversation': serialize_conversation(conversation),
            'user_message': serialize_message(user_message),
            'assistant_message': serialize_message(assistant_message),
        }

    if confident_action and email_decision.action_type == 'general_reply' and email_decision.reply.strip():
        assistant_message = append_assistant_message(
            db,
            user,
            conversation,
            content=email_decision.reply,
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level=None,
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={
                'action_type': 'general_reply',
                'status': 'complete',
                'prompt_version': EMAIL_ACTION_PROMPT_VERSION,
                'agent_name': 'email_action_agent',
                'model_name': email_decision.model_name,
                'confidence_score': email_decision.confidence_score,
            },
        )
        return {
            'conversation': serialize_conversation(conversation),
            'user_message': serialize_message(user_message),
            'assistant_message': serialize_message(assistant_message),
        }

    if confident_action and email_decision.action_type == 'needs_clarification' and email_decision.clarification_question:
        assistant_message = append_assistant_message(
            db,
            user,
            conversation,
            content=email_decision.clarification_question,
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level=None,
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={
                'action_type': 'email_clarification',
                'status': 'needs_input',
                'prompt_version': EMAIL_ACTION_PROMPT_VERSION,
                'agent_name': 'email_action_agent',
                'model_name': email_decision.model_name,
                'confidence_score': email_decision.confidence_score,
            },
        )
        return {
            'conversation': serialize_conversation(conversation),
            'user_message': serialize_message(user_message),
            'assistant_message': serialize_message(assistant_message),
        }

    contextual_question = build_contextual_question(
        conversation=conversation,
        messages=messages,
        new_message=user_message.content,
    )
    vector_store = build_pgvector_search_store(db=db, settings=settings)
    try:
        answer = answer_question_with_rag(
            db=db,
            user=user,
            question=contextual_question,
            settings=settings,
            vector_store=vector_store,
            tool_logger=tool_logger,
        )
    except Exception as exc:
        append_failed_assistant_message(
            db,
            user,
            conversation,
            reason='rag_exception',
            failure_class=exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=502,
            detail='assistant answer generation failed',
        ) from exc

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
        append_failed_assistant_message(
            db,
            user,
            conversation,
            reason='blank_answer',
            failure_class=exc.__class__.__name__,
            agent_run_id=answer.agent_run_id,
        )
        raise HTTPException(
            status_code=502,
            detail='assistant answer generation failed',
        ) from exc
    return {
        'conversation': serialize_conversation(conversation),
        'user_message': serialize_message(user_message),
        'assistant_message': serialize_message(assistant_message),
    }


@router.post('/messages/{message_id}/email/send', response_model=AssistantEmailSendResponse)
def send_assistant_email_draft(
    message_id: int,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    try:
        message = get_owned_message(db, user, message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='assistant message not found') from exc

    metadata = dict(message.metadata_ or {})
    draft = metadata.get('email_draft')
    if metadata.get('action_type') != 'email_draft' or not isinstance(draft, dict):
        raise HTTPException(status_code=422, detail='assistant message is not an email draft')
    if metadata.get('status') == 'sent':
        return {'message': serialize_message(message), 'status': 'sent'}
    if metadata.get('status') != 'pending_approval':
        raise HTTPException(status_code=409, detail='email draft is not pending approval')

    try:
        result = GmailDraftSender(settings=settings).send(
            db=db,
            to=[str(item) for item in draft.get('to', [])],
            subject=str(draft.get('subject') or ''),
            body=str(draft.get('body') or ''),
        )
    except GmailSendError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # 전송 결과는 원본 초안 메시지 metadata에 기록해 승인 이력을 남긴다.
    next_metadata = {
        **metadata,
        'status': 'sent',
        'sent_at': datetime.now(UTC).isoformat(),
        'gmail_message_id': result.message_id,
    }
    updated_message = update_message_metadata(db, user, message, next_metadata)
    return {
        'message': serialize_message(updated_message),
        'status': 'sent',
        'gmail_message_id': result.message_id,
    }
