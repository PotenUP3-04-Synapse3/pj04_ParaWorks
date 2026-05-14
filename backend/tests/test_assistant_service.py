import pytest
from sqlalchemy.orm import Session

from backend.app.assistant.service import (
    DEFAULT_CONVERSATION_TITLE,
    RECENT_CONTEXT_MESSAGE_LIMIT,
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    find_reusable_empty_conversation,
    get_owned_conversation,
    list_conversations,
    list_messages,
    summarize_conversation_title,
)
from backend.app.core.demo_auth import USERS


def test_conversations_are_scoped_to_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['hanvv-employee']
    create_conversation(db_session, viewer, title='Viewer private thread')
    create_conversation(db_session, employee, title='Employee private thread')

    viewer_conversations = list_conversations(db_session, viewer)

    assert [conversation.title for conversation in viewer_conversations] == ['Viewer private thread']


def test_get_owned_conversation_rejects_other_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['hanvv-employee']
    conversation = create_conversation(db_session, viewer, title='Viewer private thread')

    with pytest.raises(ValueError, match='assistant conversation not found'):
        get_owned_conversation(db_session, employee, conversation.id)


def test_append_messages_and_context_window(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')
    for index in range(8):
        append_user_message(db_session, viewer, conversation, f'사용자 질문 {index}')
        append_assistant_message(
            db_session,
            viewer,
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


def test_append_user_message_rejects_other_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['hanvv-employee']
    conversation = create_conversation(db_session, viewer, title='Viewer private thread')

    with pytest.raises(ValueError, match='assistant conversation not found'):
        append_user_message(db_session, employee, conversation, '권한 없는 질문')


def test_append_assistant_message_rejects_other_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['hanvv-employee']
    conversation = create_conversation(db_session, viewer, title='Viewer private thread')

    with pytest.raises(ValueError, match='assistant conversation not found'):
        append_assistant_message(
            db_session,
            employee,
            conversation,
            content='권한 없는 답변',
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level='internal',
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={},
        )


def test_append_user_message_rejects_blank_content(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')

    with pytest.raises(ValueError, match='assistant message content is required'):
        append_user_message(db_session, viewer, conversation, '   ')

    assert list_messages(db_session, viewer, conversation.id) == []


def test_append_assistant_message_rejects_blank_content(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')

    with pytest.raises(ValueError, match='assistant message content is required'):
        append_assistant_message(
            db_session,
            viewer,
            conversation,
            content='   ',
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level='internal',
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={},
        )

    assert list_messages(db_session, viewer, conversation.id) == []


def test_append_assistant_message_strips_content(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')

    message = append_assistant_message(
        db_session,
        viewer,
        conversation,
        content='  Redis 작업은 진행 중입니다.  ',
        citations=[],
        source_ids=[],
        source_links=[],
        source_snippets=[],
        permission_level='internal',
        hidden_match_count=0,
        permission_notice=None,
        agent_run_id=None,
        metadata={},
    )

    assert message.content == 'Redis 작업은 진행 중입니다.'


def test_contextual_question_excludes_matching_current_user_message(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')
    append_user_message(db_session, viewer, conversation, 'Redis 상태 알려줘')
    append_assistant_message(
        db_session,
        viewer,
        conversation,
        content='Redis 작업은 진행 중입니다.',
        citations=[],
        source_ids=[],
        source_links=[],
        source_snippets=[],
        permission_level='internal',
        hidden_match_count=0,
        permission_notice=None,
        agent_run_id=None,
        metadata={},
    )
    append_user_message(db_session, viewer, conversation, '그 다음 할 일은?')

    messages = list_messages(db_session, viewer, conversation.id)
    contextual_question = build_contextual_question(
        conversation=conversation,
        messages=messages,
        new_message='그 다음 할 일은?',
    )

    assert contextual_question.count('그 다음 할 일은?') == 1
    assert '현재 질문: 그 다음 할 일은?' in contextual_question


def test_finds_only_one_reusable_empty_conversation(db_session: Session) -> None:
    viewer = USERS['viewer']
    reusable = create_conversation(db_session, viewer, title=DEFAULT_CONVERSATION_TITLE)
    filled = create_conversation(db_session, viewer, title=DEFAULT_CONVERSATION_TITLE)
    append_user_message(db_session, viewer, filled, '이미 사용한 대화입니다')

    empty_conversation = find_reusable_empty_conversation(db_session, viewer)

    assert empty_conversation is not None
    assert empty_conversation.id == reusable.id


def test_first_user_message_sets_short_chat_history_title(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title=DEFAULT_CONVERSATION_TITLE)
    question = '이번 주 목요일 오전 회의 일정과 준비할 문서를 기획팀 관점에서 정리해줘'

    append_user_message(db_session, viewer, conversation, question)

    db_session.refresh(conversation)
    assert conversation.title == summarize_conversation_title(question)
    assert len(conversation.title) <= 32
    assert conversation.title.endswith('…')
