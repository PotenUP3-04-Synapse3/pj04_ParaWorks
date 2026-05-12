from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.demo_auth import DemoUser
from backend.app.models import AssistantConversation, AssistantMessage

RECENT_CONTEXT_MESSAGE_LIMIT = 6
DEFAULT_CONVERSATION_TITLE = '새 대화'


def create_conversation(db: Session, user: DemoUser, *, title: str | None = None) -> AssistantConversation:
    conversation = AssistantConversation(
        user_id=user.id,
        title=_conversation_title(title),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, user: DemoUser) -> list[AssistantConversation]:
    return list(
        db.scalars(
            select(AssistantConversation)
            .where(AssistantConversation.user_id == user.id)
            .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc())
        )
    )


def get_owned_conversation(db: Session, user: DemoUser, conversation_id: int) -> AssistantConversation:
    conversation = db.scalar(
        select(AssistantConversation)
        .options(selectinload(AssistantConversation.messages))
        .where(
            AssistantConversation.id == conversation_id,
            AssistantConversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise ValueError('assistant conversation not found')
    return conversation


def list_messages(db: Session, user: DemoUser, conversation_id: int) -> list[AssistantMessage]:
    conversation = get_owned_conversation(db, user, conversation_id)
    return list(conversation.messages)


def append_user_message(db: Session, conversation: AssistantConversation, content: str) -> AssistantMessage:
    message = AssistantMessage(
        conversation_id=conversation.id,
        role='user',
        content=content.strip(),
    )
    conversation.updated_at = datetime.now(UTC)
    if conversation.title == DEFAULT_CONVERSATION_TITLE:
        conversation.title = _conversation_title(content)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


def append_assistant_message(
    db: Session,
    conversation: AssistantConversation,
    *,
    content: str,
    citations: list,
    source_ids: list,
    source_links: list,
    source_snippets: list,
    permission_level: str | None,
    hidden_match_count: int,
    permission_notice: str | None,
    agent_run_id: int | None,
    metadata: dict,
) -> AssistantMessage:
    message = AssistantMessage(
        conversation_id=conversation.id,
        role='assistant',
        content=content,
        citations=citations,
        source_ids=source_ids,
        source_links=source_links,
        source_snippets=source_snippets,
        permission_level=permission_level,
        hidden_match_count=hidden_match_count,
        permission_notice=permission_notice,
        agent_run_id=agent_run_id,
        metadata_=metadata,
    )
    conversation.updated_at = datetime.now(UTC)
    conversation.summary = update_summary(conversation.summary, message.content)
    conversation.summary_updated_at = datetime.now(UTC)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


def build_contextual_question(
    *,
    conversation: AssistantConversation,
    messages: list[AssistantMessage],
    new_message: str,
) -> str:
    parts: list[str] = []
    if conversation.summary:
        parts.append(f'대화 요약: {conversation.summary}')

    # 전체 대화를 보내지 않고 최근 메시지만 사용해 토큰 사용량을 제한한다.
    recent_messages = messages[-RECENT_CONTEXT_MESSAGE_LIMIT:]
    if recent_messages:
        parts.append('최근 대화:')
        parts.extend(f'{message.role}: {message.content}' for message in recent_messages)

    parts.append(f'현재 질문: {new_message.strip()}')
    return '\n'.join(parts)


def update_summary(existing_summary: str | None, latest_answer: str) -> str:
    summary_basis = f'{existing_summary or ""}\n{latest_answer}'.strip()
    return summary_basis[:1000]


def serialize_conversation(conversation: AssistantConversation) -> dict:
    return {
        'id': conversation.id,
        'title': conversation.title,
        'summary': conversation.summary,
        'created_at': conversation.created_at.isoformat(),
        'updated_at': conversation.updated_at.isoformat(),
    }


def serialize_message(message: AssistantMessage) -> dict:
    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'role': message.role,
        'content': message.content,
        'citations': message.citations,
        'source_ids': message.source_ids,
        'source_links': message.source_links,
        'source_snippets': message.source_snippets,
        'permission_level': message.permission_level,
        'hidden_match_count': message.hidden_match_count,
        'permission_notice': message.permission_notice,
        'agent_run_id': message.agent_run_id,
        'metadata': message.metadata_,
        'created_at': message.created_at.isoformat(),
    }


def _conversation_title(value: str | None) -> str:
    normalized = (value or DEFAULT_CONVERSATION_TITLE).strip() or DEFAULT_CONVERSATION_TITLE
    return normalized[:80]
