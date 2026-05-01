import math

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models import (
    DecisionRecord,
    Document,
    DocumentChunk,
    DocumentVersion,
    Source,
    Todo,
)
from backend.app.rag.embeddings import DeterministicHashEmbeddingModel
from backend.app.rag.indexing import build_rag_index_documents, index_vector_documents
from backend.app.rag.vector_store import VectorDocument


class RecordingVectorWriter:
    def __init__(self) -> None:
        self.upserts: list[tuple[VectorDocument, list[float]]] = []

    def upsert_with_embedding(self, document: VectorDocument, embedding: list[float]) -> None:
        self.upserts.append((document, embedding))


def seed_chunk(db: Session, text: str, source_id: str = 'gmail-index-source') -> int:
    source = Source(
        source_type='gmail',
        source_id=source_id,
        source_url=f'https://gmail.mock/{source_id}',
        title='Index source',
        author='owner@example.com',
        permission_level='internal',
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

    chunk = DocumentChunk(
        version_id=version.id,
        source_id=source.id,
        chunk_index=0,
        text=text,
        source_snippet=text[:240],
        permission_level='internal',
        metadata_={'source_url': source.source_url, 'source_type': source.source_type},
    )
    db.add(chunk)
    db.commit()
    return chunk.id


def test_hash_embedding_is_stable_and_normalized() -> None:
    model = DeterministicHashEmbeddingModel(dimensions=8)

    first = model.embed('Redis queue Redis 한국어 업무')
    second = model.embed('Redis queue Redis 한국어 업무')

    assert first == second
    assert len(first) == 8
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_index_vector_documents_writes_embeddings() -> None:
    writer = RecordingVectorWriter()
    documents = [
        VectorDocument(
            document_id='chunk:1',
            text='Redis queue state',
            source_url='https://gmail.mock/chunk-1',
            source_snippet='Redis queue state',
            permission_level='internal',
            metadata={'source_type': 'gmail'},
        )
    ]

    result = index_vector_documents(
        documents=documents,
        writer=writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
    )

    assert result.indexed_count == 1
    assert result.embedding_dimensions == 8
    assert result.document_ids == ['chunk:1']
    assert writer.upserts[0][0] == documents[0]
    assert len(writer.upserts[0][1]) == 8


def test_build_rag_index_documents_includes_chunks_and_approved_knowledge(db_session: Session) -> None:
    chunk_id = seed_chunk(db_session, 'Redis queue state should be indexed for RAG.')
    approved = DecisionRecord(
        title='Use pgvector for RAG',
        decision_summary='PostgreSQL pgvector stores durable company memory embeddings.',
        source_links=['https://knowledge.mock/pgvector'],
        source_snippets=['pgvector decision snippet'],
        confidence_score=0.9,
        permission_level='internal',
        review_status='approved',
    )
    pending = Todo(
        title='Draft pending item',
        priority='medium',
        priority_reason='Pending records must not enter the serving index yet.',
        source_links=['https://knowledge.mock/pending'],
        source_snippets=['pending snippet'],
        confidence_score=0.7,
        permission_level='internal',
        review_status='pending_review',
    )
    db_session.add_all([approved, pending])
    db_session.commit()

    documents = build_rag_index_documents(db_session)

    assert [document.document_id for document in documents] == [
        f'chunk:{chunk_id}',
        f'decision_record:{approved.id}',
    ]
    assert documents[0].metadata['source_type'] == 'gmail'
    assert documents[1].source_url == 'https://knowledge.mock/pgvector'


def test_reindex_endpoint_returns_dry_run_index_summary(client: TestClient, db_session: Session) -> None:
    seed_chunk(db_session, 'Slack and Gmail history should be embedded for search.', 'gmail-api-index')

    response = client.post('/api/v1/rag/reindex')

    assert response.status_code == 200
    assert response.json() == {
        'dry_run': True,
        'indexed_count': 1,
        'embedding_dimensions': 16,
        'document_ids': ['chunk:1'],
        'storage_backend': 'preview',
    }
