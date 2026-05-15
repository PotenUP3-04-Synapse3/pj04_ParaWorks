from contextlib import suppress

from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.agents.rag_orchestrator_agent.service import (
    build_default_rag_orchestrator_agent,
)
from backend.app.core.config import Settings
from backend.app.core.demo_auth import USERS
from backend.app.models import (
    AgentRun,
    DecisionRecord,
    Document,
    DocumentChunk,
    DocumentVersion,
    Source,
    Todo,
)
from backend.app.rag.vector_store import InMemoryVectorStore, VectorDocument


def seed_chunk(db: Session, source_type: str, source_id: str, text: str, permission_level: str) -> None:
    source = Source(
        source_type=source_type,
        source_id=source_id,
        source_url=f'https://{source_type}.mock/{source_id}',
        title=f'{source_type} evidence',
        author='owner@example.com',
        permission_level=permission_level,
        raw_metadata={'ts': '2026-04-30T10:00:00+00:00'},
    )
    db.add(source)
    db.flush()

    document = Document(source_id=source.id, title=source.title, current_version='v1')
    db.add(document)
    db.flush()

    version = DocumentVersion(document_id=document.id, version='v1', body=text)
    db.add(version)
    db.flush()

    db.add(
        DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=0,
            text=text,
            source_snippet=text[:240],
            permission_level=permission_level,
            metadata_={'source_url': source.source_url, 'source_type': source_type},
        )
    )
    db.commit()


def test_rag_service_answers_from_visible_chunks(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'gmail',
        'gmail-redis',
        'Redis should be used for transient job state while PostgreSQL stores durable records.',
        'internal',
    )

    answer = answer_question_with_rag(db=db_session, user=USERS['viewer'], question='Redis job state')

    assert answer.answer
    assert answer.source_links == ['https://gmail.mock/gmail-redis']
    assert answer.permission_notice is None
    assert answer.hidden_match_count == 0


def test_rag_service_hides_restricted_chunks_for_viewer(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'drive',
        'drive-pricing',
        'Confidential pricing uses Redis reserved capacity.',
        'restricted',
    )

    answer = answer_question_with_rag(db=db_session, user=USERS['viewer'], question='confidential pricing')

    assert answer.answer == '권한 내에서 확인 가능한 근거를 찾지 못했습니다.'
    assert answer.source_links == []
    assert answer.hidden_match_count == 1
    assert answer.permission_notice == 'Some sources may be hidden by permissions.'


def test_rag_service_persists_agent_run_metadata(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'gmail',
        'gmail-rag-agent-run',
        'Redis should be used for transient job state while PostgreSQL stores durable records.',
        'internal',
    )

    answer = answer_question_with_rag(db=db_session, user=USERS['viewer'], question='Redis job state')

    agent_run = db_session.query(AgentRun).one()
    assert answer.agent_run_id == agent_run.id
    assert agent_run.agent_name == 'rag_orchestrator_agent'
    assert agent_run.prompt_version == 'rag-answer:v1'
    assert agent_run.status == 'complete'
    assert agent_run.source_window == 'ask:Redis job state'
    assert agent_run.model_name == answer.cost.model_name
    assert agent_run.input_tokens == answer.cost.token_usage.input_tokens
    assert agent_run.output_tokens == answer.cost.token_usage.output_tokens
    assert agent_run.total_tokens == answer.cost.token_usage.total_tokens
    assert agent_run.estimated_cost_usd == answer.cost.estimated_cost_usd
    assert agent_run.permission_level == 'internal'
    assert agent_run.cache_key == answer.cache_key
    assert agent_run.metadata_['question'] == 'Redis job state'
    assert agent_run.metadata_['source_count'] == 1
    assert agent_run.metadata_['hidden_match_count'] == 0


def test_rag_service_answers_from_approved_knowledge_records(db_session: Session) -> None:
    db_session.add(
        DecisionRecord(
            title='Use Redis for queues',
            decision_summary='Redis should power queue and job progress updates.',
            source_links=['https://knowledge.mock/redis-decision'],
            source_snippets=['Approved Redis decision snippet'],
            confidence_score=0.91,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    answer = answer_question_with_rag(db=db_session, user=USERS['viewer'], question='Redis queues')

    assert answer.answer
    assert answer.source_links == ['https://knowledge.mock/redis-decision']
    assert answer.source_snippets == ['Approved Redis decision snippet']
    assert answer.hidden_match_count == 0
    assert answer.permission_notice is None


def test_rag_service_hides_restricted_approved_knowledge_for_viewer(db_session: Session) -> None:
    db_session.add(
        Todo(
            title='Review confidential pricing',
            priority='high',
            priority_reason='Confidential pricing requires finance approval.',
            source_links=['https://knowledge.mock/restricted-pricing'],
            source_snippets=['Restricted pricing snippet'],
            confidence_score=0.8,
            permission_level='restricted',
            review_status='approved',
        )
    )
    db_session.commit()

    answer = answer_question_with_rag(db=db_session, user=USERS['viewer'], question='confidential pricing')

    assert answer.answer == '권한 내에서 확인 가능한 근거를 찾지 못했습니다.'
    assert answer.source_links == []
    assert answer.hidden_match_count == 1
    assert answer.permission_notice == 'Some sources may be hidden by permissions.'


def test_rag_service_can_answer_from_vector_store_matches(db_session: Session) -> None:
    vector_store = InMemoryVectorStore()
    vector_store.upsert(
        VectorDocument(
            document_id='chunk:vector-alpha',
            text='Project Alpha launch history came from the indexed company memory vector store.',
            source_url='https://vector.mock/project-alpha',
            source_snippet='Project Alpha launch history',
            permission_level='internal',
            metadata={'source_type': 'vector_test'},
        )
    )

    answer = answer_question_with_rag(
        db=db_session,
        user=USERS['viewer'],
        question='Project Alpha launch history',
        vector_store=vector_store,
    )

    assert answer.answer
    assert answer.source_links == ['https://vector.mock/project-alpha']
    assert answer.source_snippets == ['Project Alpha launch history']
    assert answer.hidden_match_count == 0


def test_rag_service_uses_configured_stronger_primary_model(monkeypatch) -> None:
    captured = {}

    def fake_build_langchain_rag_orchestrator_model(settings):
        captured['primary'] = settings.openai_primary_model
        captured['fallback'] = settings.openai_fallback_model
        raise RuntimeError('stop after settings capture')

    monkeypatch.setattr(
        'backend.app.agents.rag_orchestrator_agent.service.build_langchain_rag_orchestrator_model',
        fake_build_langchain_rag_orchestrator_model,
    )

    with suppress(RuntimeError):
        build_default_rag_orchestrator_agent(
            Settings(
                paraworks_demo_mode=False,
                openai_api_key='test-key',
                agent_llm_enabled=True,
                agent_llm_openai_primary_model='gpt-5.4',
                agent_llm_openai_model='gpt-5.4-mini',
            )
        )

    assert captured == {
        'primary': 'gpt-5.4',
        'fallback': 'gpt-5.4-mini',
    }
