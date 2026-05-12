import pytest
from sqlalchemy.orm import Session

from backend.app.assistant.service import (
    RECENT_CONTEXT_MESSAGE_LIMIT,
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    get_owned_conversation,
    list_conversations,
    list_messages,
)
from backend.app.core.demo_auth import USERS


def test_conversations_are_scoped_to_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['employee-jun']
    create_conversation(db_session, viewer, title='Viewer private thread')
    create_conversation(db_session, employee, title='Employee private thread')

    viewer_conversations = list_conversations(db_session, viewer)

    assert [conversation.title for conversation in viewer_conversations] == ['Viewer private thread']


def test_get_owned_conversation_rejects_other_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['employee-jun']
    conversation = create_conversation(db_session, viewer, title='Viewer private thread')

    with pytest.raises(ValueError, match='assistant conversation not found'):
        get_owned_conversation(db_session, employee, conversation.id)


def test_append_messages_and_context_window(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')
    for index in range(8):
        append_user_message(db_session, conversation, f'사용자 질문 {index}')
        append_assistant_message(
            db_session,
            conversation,
            content=f'비서 답변 {index}',
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level='internal',
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={'turn': index},
        )
    conversation.summary = '이전 대화는 Redis 작업 상태에 관한 내용입니다.'
    db_session.commit()

    messages = list_messages(db_session, viewer, conversation.id)
    contextual_question = build_contextual_question(
        conversation=conversation,
        messages=messages,
        new_message='그 다음 할 일은?',
    )

    assert len(messages) == 16
    assert '대화 요약: 이전 대화는 Redis 작업 상태에 관한 내용입니다.' in contextual_question
    assert '현재 질문: 그 다음 할 일은?' in contextual_question
    assert '사용자 질문 0' not in contextual_question
    assert '비서 답변 7' in contextual_question
    assert contextual_question.count('assistant:') <= RECENT_CONTEXT_MESSAGE_LIMIT // 2 + 1
