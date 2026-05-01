from sqlalchemy.orm import Session

from backend.app.agent_runtime.company_memory import (
    run_company_memory_agent_orchestration,
)
from backend.app.core.demo_auth import USERS
from backend.app.models import (
    AgentRun,
    Document,
    DocumentChunk,
    DocumentVersion,
    ReviewItem,
    Source,
)


def seed_chunk(db: Session, source_type: str, source_id: str, text: str, permission_level: str = 'internal') -> None:
    source = Source(
        source_type=source_type,
        source_id=source_id,
        source_url=f'https://{source_type}.mock/{source_id}',
        title=f'{source_type} evidence',
        author='owner@example.com',
        permission_level=permission_level,
        raw_metadata={'ts': '2026-05-02T09:00:00+09:00'},
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


def test_company_memory_orchestration_runs_real_agent_services(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'slack',
        'slack-redis',
        'Redis should support queue and job progress workflows.',
    )
    seed_chunk(
        db_session,
        'gmail',
        'gmail-redis',
        'PostgreSQL remains the durable source of record while Redis handles transient job state.',
    )

    result = run_company_memory_agent_orchestration(
        db=db_session,
        user=USERS['admin'],
        question='Redis job state',
    )

    assert result.backend == 'langgraph'
    assert result.completed_nodes == [
        'collect_evidence',
        'draft_review_candidates',
        'retrieve_company_memory',
        'answer_with_rag',
    ]
    assert result.outputs['slack_review_items_created'] == 1
    assert result.outputs['mail_document_review_items_created'] == 1
    assert result.outputs['rag_agent_run_created'] is True
    assert result.outputs['token_budget_policy'] == 'delta_sync_hash_skip_evidence_budget'

    agent_names = [run.agent_name for run in db_session.query(AgentRun).order_by(AgentRun.id).all()]
    assert agent_names == ['slack_agent', 'mail_document_agent', 'rag_orchestrator_agent']

    review_items = db_session.query(ReviewItem).order_by(ReviewItem.id).all()
    assert len(review_items) == 2
    assert {item.payload['agent_name'] for item in review_items} == {'slack_agent', 'mail_document_agent'}
