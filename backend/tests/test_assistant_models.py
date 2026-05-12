from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import AssistantConversation, AssistantMessage


def test_assistant_conversation_and_messages_persist(db_session: Session) -> None:
    conversation = AssistantConversation(
        user_id='employee-mina',
        title='Redis 회의 준비',
        summary='Redis 관련 이전 대화 요약',
    )
    db_session.add(conversation)
    db_session.flush()

    message = AssistantMessage(
        conversation_id=conversation.id,
        role='assistant',
        content='Redis는 일시적인 작업 상태 공유에 사용됩니다.',
        citations=[
            {
                'source_id': 'gmail-redis',
                'source_url': 'https://gmail.mock/redis',
                'permission_level': 'internal',
            }
        ],
        source_ids=['gmail-redis'],
        source_links=['https://gmail.mock/redis'],
        source_snippets=['Redis 작업 상태 근거'],
        permission_level='internal',
        hidden_match_count=0,
        permission_notice=None,
        agent_run_id=7,
        metadata_={'retrieval_backend': 'deterministic_lexical'},
    )
    db_session.add(message)
    db_session.commit()

    stored = db_session.scalar(
        select(AssistantConversation).where(AssistantConversation.user_id == 'employee-mina')
    )

    assert stored is not None
    assert stored.title == 'Redis 회의 준비'
    assert stored.summary == 'Redis 관련 이전 대화 요약'
    assert len(stored.messages) == 1
    assert stored.messages[0].content == 'Redis는 일시적인 작업 상태 공유에 사용됩니다.'
    assert stored.messages[0].citations[0]['source_id'] == 'gmail-redis'
    assert stored.messages[0].agent_run_id == 7
