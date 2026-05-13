from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.demo_auth import DemoUser
from backend.app.models import AssistantConversation, AssistantMessage

RECENT_CONTEXT_MESSAGE_LIMIT = 6
DEFAULT_CONVERSATION_TITLE = '새 대화'
MAX_CONVERSATION_TITLE_LENGTH = 32


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


def find_reusable_empty_conversation(db: Session, user: DemoUser) -> AssistantConversation | None:
    return db.scalar(
        select(AssistantConversation)
        .where(
            AssistantConversation.user_id == user.id,
            AssistantConversation.title == DEFAULT_CONVERSATION_TITLE,
            ~AssistantConversation.messages.any(),
        )
        .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc())
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


def get_owned_message(db: Session, user: DemoUser, message_id: int) -> AssistantMessage:
    message = db.scalar(
        select(AssistantMessage)
        .join(AssistantConversation)
        .where(
            AssistantMessage.id == message_id,
            AssistantConversation.user_id == user.id,
        )
    )
    if message is None:
        raise ValueError('assistant message not found')
    return message


def append_user_message(
    db: Session,
    user: DemoUser,
    conversation: AssistantConversation,
    content: str,
) -> AssistantMessage:
    _ensure_owned_conversation(user, conversation)
    normalized_content = content.strip()
    if not normalized_content:
        raise ValueError('assistant message content is required')

    message = AssistantMessage(
        conversation_id=conversation.id,
        role='user',
        content=normalized_content,
    )
    conversation.updated_at = datetime.now(UTC)
    if conversation.title == DEFAULT_CONVERSATION_TITLE:
        conversation.title = summarize_conversation_title(normalized_content)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


def update_message_metadata(
    db: Session,
    user: DemoUser,
    message: AssistantMessage,
    metadata: dict,
) -> AssistantMessage:
    conversation = get_owned_conversation(db, user, message.conversation_id)
    _ensure_owned_conversation(user, conversation)
    # MutableDict 변경 감지를 확실하게 만들기 위해 새 dict 인스턴스로 교체한다.
    message.metadata_ = dict(metadata)
    conversation.updated_at = datetime.now(UTC)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


def append_assistant_message(
    db: Session,
    user: DemoUser,
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
    _ensure_owned_conversation(user, conversation)
    normalized_content = content.strip()
    if not normalized_content:
        raise ValueError('assistant message content is required')

    message = AssistantMessage(
        conversation_id=conversation.id,
        role='assistant',
        content=normalized_content,
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
    seen_context: set[str] = set()
    if conversation.summary:
        summary_lines = _dedupe_lines(conversation.summary.splitlines())
        if summary_lines:
            seen_context.update(f'assistant:{line}' for line in summary_lines)
            parts.append(f"대화 요약: {' '.join(summary_lines)}")

    # 전체 대화를 보내지 않고 최근 메시지만 사용해 토큰 사용량을 제한한다.
    context_messages = _exclude_current_user_message(messages, new_message)
    recent_messages = context_messages[-RECENT_CONTEXT_MESSAGE_LIMIT:]
    if recent_messages:
        parts.append('최근 대화:')
        for message in recent_messages:
            content = _compact_context_text(message.content)
            dedupe_key = f'{message.role}:{content}'
            if not content or dedupe_key in seen_context:
                continue
            seen_context.add(dedupe_key)
            parts.append(f'{message.role}: {content}')
        parts.extend(f'{message.role}: {message.content}' for message in recent_messages)

    parts.append(f'현재 질문: {new_message.strip()}')
    return '\n'.join(parts)


def update_summary(existing_summary: str | None, latest_answer: str) -> str:
    lines = [*(existing_summary or '').splitlines(), latest_answer]
    return '\n'.join(_dedupe_lines(lines)[-MAX_SUMMARY_LINES:])[:1000]


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


def summarize_conversation_title(value: str) -> str:
    normalized = ' '.join(value.strip().split())
    if not normalized:
        return DEFAULT_CONVERSATION_TITLE
    if len(normalized) <= MAX_CONVERSATION_TITLE_LENGTH:
        return normalized
    return f'{normalized[: MAX_CONVERSATION_TITLE_LENGTH - 1].rstrip()}…'


def _ensure_owned_conversation(user: DemoUser, conversation: AssistantConversation) -> None:
    if conversation.user_id != user.id:
        raise ValueError('assistant conversation not found')


def _exclude_current_user_message(
    messages: list[AssistantMessage],
    new_message: str,
) -> list[AssistantMessage]:
    if not messages:
        return messages
    latest_message = messages[-1]
    if latest_message.role == 'user' and latest_message.content.strip() == new_message.strip():
        return messages[:-1]
    return messages


def _compact_context_text(value: str) -> str:
    compacted = ' '.join(value.strip().split())
    if len(compacted) <= MAX_CONTEXT_MESSAGE_CHARS:
        return compacted
    return f'{compacted[: MAX_CONTEXT_MESSAGE_CHARS - 1].rstrip()}…'


def _dedupe_lines(lines: list[str]) -> list[str]:
    unique_lines: list[str] = []
    seen: set[str] = set()
    for line in lines:
        compacted = _compact_context_text(line)
        if not compacted or compacted in seen:
            continue
        seen.add(compacted)
        unique_lines.append(compacted)
    return unique_lines
