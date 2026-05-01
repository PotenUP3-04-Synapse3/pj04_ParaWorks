import math

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models import (
    DecisionRecord,
    Document,
    DocumentChunk,
    DocumentVersion,
    Source,
    SyncJob,
    Todo,
    VectorIndexState,
)
from backend.app.rag.embeddings import (
    DeterministicHashEmbeddingModel,
    EmbeddingBatchResult,
)
from backend.app.rag.indexing import (
    build_rag_index_documents,
    compute_vector_document_hash,
    index_changed_vector_documents,
    index_vector_documents,
)
from backend.app.rag.vector_store import VectorDocument


class RecordingVectorWriter:
    def __init__(self) -> None:
        self.upserts: list[tuple[VectorDocument, list[float]]] = []

    def upsert_with_embedding(self, document: VectorDocument, embedding: list[float]) -> None:
        self.upserts.append((document, embedding))


class RecordingBatchEmbeddingModel:
    dimensions = 2

    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed(self, text: str) -> list[float]:
        raise AssertionError('index_changed_vector_documents should call embed_many')

    def embed_many(self, texts: list[str]) -> EmbeddingBatchResult:
        self.batches.append(texts)
        return EmbeddingBatchResult(
            embeddings=[[float(index), float(index + 1)] for index, _ in enumerate(texts)],
            prompt_tokens=10 * len(texts),
            total_tokens=10 * len(texts),
            request_count=1 if texts else 0,
        )


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


def test_vector_document_hash_changes_when_serving_content_changes() -> None:
    original = VectorDocument(
        document_id='chunk:1',
        text='Redis queue state',
        source_url='https://gmail.mock/chunk-1',
        source_snippet='Redis queue state',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )
    changed = VectorDocument(
        document_id='chunk:1',
        text='Redis queue state with new approval rule',
        source_url='https://gmail.mock/chunk-1',
        source_snippet='Redis queue state',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )

    assert compute_vector_document_hash(original) != compute_vector_document_hash(changed)


def test_incremental_indexing_skips_unchanged_documents_after_success(db_session: Session) -> None:
    document = VectorDocument(
        document_id='chunk:1',
        text='Redis queue state',
        source_url='https://gmail.mock/chunk-1',
        source_snippet='Redis queue state',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )
    first_writer = RecordingVectorWriter()

    first_result = index_changed_vector_documents(
        db=db_session,
        documents=[document],
        writer=first_writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
        embedding_model_name='deterministic-hash:test',
    )
    second_writer = RecordingVectorWriter()
    second_result = index_changed_vector_documents(
        db=db_session,
        documents=[document],
        writer=second_writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
        embedding_model_name='deterministic-hash:test',
    )

    state = db_session.query(VectorIndexState).one()
    assert first_result.indexed_count == 1
    assert second_result.indexed_count == 0
    assert second_result.skipped_count == 1
    assert second_result.saved_embedding_calls == 1
    assert second_writer.upserts == []
    assert state.status == 'indexed'
    assert state.content_hash == compute_vector_document_hash(document)


def test_incremental_indexing_reindexes_changed_documents(db_session: Session) -> None:
    original = VectorDocument(
        document_id='chunk:1',
        text='Redis queue state',
        source_url='https://gmail.mock/chunk-1',
        source_snippet='Redis queue state',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )
    changed = VectorDocument(
        document_id='chunk:1',
        text='Redis queue state with changed retention policy',
        source_url='https://gmail.mock/chunk-1',
        source_snippet='Redis queue state with changed retention policy',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )

    index_changed_vector_documents(
        db=db_session,
        documents=[original],
        writer=RecordingVectorWriter(),
        embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
        embedding_model_name='deterministic-hash:test',
    )
    second_writer = RecordingVectorWriter()
    result = index_changed_vector_documents(
        db=db_session,
        documents=[changed],
        writer=second_writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
        embedding_model_name='deterministic-hash:test',
    )

    state = db_session.query(VectorIndexState).one()
    assert result.indexed_count == 1
    assert result.skipped_count == 0
    assert len(second_writer.upserts) == 1
    assert state.content_hash == compute_vector_document_hash(changed)


def test_incremental_indexing_batches_only_changed_documents(db_session: Session) -> None:
    unchanged = VectorDocument(
        document_id='chunk:1',
        text='Already indexed document',
        source_url='https://gmail.mock/chunk-1',
        source_snippet='Already indexed document',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )
    changed = VectorDocument(
        document_id='chunk:2',
        text='New document needs embedding',
        source_url='https://gmail.mock/chunk-2',
        source_snippet='New document needs embedding',
        permission_level='internal',
        metadata={'source_type': 'gmail'},
    )
    index_changed_vector_documents(
        db=db_session,
        documents=[unchanged],
        writer=RecordingVectorWriter(),
        embedding_model=DeterministicHashEmbeddingModel(dimensions=2),
        embedding_model_name='deterministic-hash:test',
    )
    embedding_model = RecordingBatchEmbeddingModel()
    writer = RecordingVectorWriter()

    result = index_changed_vector_documents(
        db=db_session,
        documents=[unchanged, changed],
        writer=writer,
        embedding_model=embedding_model,
        embedding_model_name='deterministic-hash:test',
    )

    assert embedding_model.batches == [['New document needs embedding']]
    assert result.indexed_count == 1
    assert result.skipped_count == 1
    assert result.saved_embedding_calls == 1
    assert result.embedding_request_count == 1
    assert result.embedding_prompt_tokens == 10
    assert [document.document_id for document, _ in writer.upserts] == ['chunk:2']


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
        'skipped_count': 0,
        'saved_embedding_calls': 0,
        'embedding_request_count': 1,
        'embedding_prompt_tokens': 0,
        'embedding_total_tokens': 0,
        'embedding_dimensions': 16,
        'document_ids': ['chunk:1'],
        'skipped_document_ids': [],
        'incremental': True,
        'storage_backend': 'preview',
    }


def test_reindex_endpoint_reports_skipped_documents_from_index_state(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_chunk(db_session, 'Slack and Gmail history should be embedded for search.', 'gmail-api-index')
    document = build_rag_index_documents(db_session)[0]
    index_changed_vector_documents(
        db=db_session,
        documents=[document],
        writer=RecordingVectorWriter(),
        embedding_model=DeterministicHashEmbeddingModel(dimensions=16),
        embedding_model_name='deterministic-hash:v1',
    )

    response = client.post('/api/v1/rag/reindex')

    assert response.status_code == 200
    assert response.json()['indexed_count'] == 0
    assert response.json()['skipped_count'] == 1
    assert response.json()['saved_embedding_calls'] == 1


def test_reindex_endpoint_rejects_pgvector_write_without_postgres(client: TestClient) -> None:
    response = client.post('/api/v1/rag/reindex?dry_run=false')

    assert response.status_code == 400
    assert response.json()['detail'] == 'pgvector writes require a PostgreSQL database.'


def test_reindex_job_endpoint_records_indexing_job(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_chunk(db_session, 'Slack and Gmail history should be embedded for search.', 'gmail-job-index')

    response = client.post('/api/v1/rag/reindex/jobs')

    assert response.status_code == 200
    body = response.json()
    assert body['job_id'].startswith('rag-index-')
    assert body['status'] == 'complete'
    assert body['indexed_count'] == 1
    assert body['skipped_count'] == 0
    assert body['saved_embedding_calls'] == 0
    job = db_session.query(SyncJob).one()
    assert job.job_id == body['job_id']
    assert job.connector_type == 'rag-index'
    assert job.status == 'complete'
    assert job.progress_pct == 100
    assert job.message == 'indexed=1 skipped=0 saved_embedding_calls=0'


def test_rag_indexing_summary_returns_latest_jobs_and_state_counts(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_chunk(db_session, 'Slack and Gmail history should be embedded for search.', 'gmail-summary-index')
    db_session.add(
        VectorIndexState(
            document_id='chunk:existing',
            embedding_model='deterministic-hash:v1',
            embedding_dimensions=16,
            content_hash='abc123',
            status='indexed',
        )
    )
    db_session.commit()
    client.post('/api/v1/rag/reindex/jobs')

    response = client.get('/api/v1/rag/indexing/summary')

    assert response.status_code == 200
    body = response.json()
    assert body['state_counts'] == {'indexed': 1}
    assert body['latest_jobs'][0]['connector_type'] == 'rag-index'
    assert body['latest_jobs'][0]['status'] == 'complete'
    assert body['latest_jobs'][0]['indexed_count'] == 1
    assert body['latest_jobs'][0]['skipped_count'] == 0
    assert body['latest_jobs'][0]['saved_embedding_calls'] == 0
