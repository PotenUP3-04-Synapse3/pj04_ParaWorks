from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import PermissionContext
from backend.app.agents.memory_extraction_agent import (
    DEFAULT_MEMORY_EXTRACTION_AGENTS,
    build_memory_extraction_evidence_packet,
    create_memory_extraction_review_items,
)
from backend.app.models import (
    AgentRun,
    Document,
    DocumentChunk,
    DocumentVersion,
    ReviewItem,
    Source,
)


def seed_chunk(db: Session, source_type: str, source_id: str, text: str) -> None:
    source = Source(
        source_type=source_type,
        source_id=source_id,
        source_url=f'https://{source_type}.mock/{source_id}',
        title=f'{source_type} evidence',
        author='owner@example.com',
        permission_level='internal',
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
            permission_level='internal',
            metadata_={'source_url': source.source_url, 'source_type': source_type},
        )
    )
    db.commit()


def test_memory_extraction_agents_persist_review_items_and_agent_runs(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'slack',
        'slack-decision',
        '결정: Redis를 작업 상태 공유에 사용합니다. TODO: 런칭 전에 권한 테스트를 마칩니다.',
    )
    seed_chunk(
        db_session,
        'gmail',
        'gmail-history',
        'QA 완료 후 배포했습니다. 이유는 고객 데모 일정이 확정되었기 때문입니다.',
    )
    packet = build_memory_extraction_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='orchestrated-memory:all',
    )

    created = create_memory_extraction_review_items(
        db=db_session,
        packet=packet,
        agents=DEFAULT_MEMORY_EXTRACTION_AGENTS,
    )

    assert len(created) == 4
    assert {item.item_type for item in created} == {'timeline_event', 'history_event', 'decision_record', 'todo'}
    assert next(item for item in created if item.item_type == 'todo').payload['priority'] == 'high'
    assert next(item for item in created if item.item_type == 'decision_record').payload['decision_summary']

    agent_runs = db_session.scalars(select(AgentRun).order_by(AgentRun.id)).all()
    assert [run.agent_name for run in agent_runs] == [
        'timeline_agent',
        'history_agent',
        'decision_record_agent',
        'todo_agent',
    ]
    assert all(run.metadata_['validation_status'] == 'accepted' for run in agent_runs)

    stored_items = db_session.scalars(select(ReviewItem).order_by(ReviewItem.id)).all()
    assert [item.id for item in stored_items] == [item.id for item in created]
