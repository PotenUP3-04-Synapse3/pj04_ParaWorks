from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.core.demo_auth import USERS
from backend.app.models import Document, DocumentChunk, DocumentVersion, Source


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
