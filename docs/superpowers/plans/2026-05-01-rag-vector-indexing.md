# RAG Vector Indexing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first vector indexing pipeline that turns current company memory into embeddable `VectorDocument` records.

**Architecture:** Keep vector indexing behind a small writer protocol so local smoke can use deterministic preview mode while production can write to `PgVectorStore`. Source chunks and approved knowledge records are collected in a stable order, embedded, and written with permission metadata intact.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, PostgreSQL + pgvector adapter, deterministic local hash embeddings for tests.

---

### Task 1: Deterministic Local Embeddings

**Files:**
- Create: `backend/app/rag/embeddings.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing test**

```python
def test_hash_embedding_is_stable_and_normalized() -> None:
    model = DeterministicHashEmbeddingModel(dimensions=8)

    first = model.embed('Redis queue Redis 한국어 업무')
    second = model.embed('Redis queue Redis 한국어 업무')

    assert first == second
    assert len(first) == 8
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.rag.embeddings'`.

- [x] **Step 3: Write minimal implementation**

Create `EmbeddingModel` protocol and `DeterministicHashEmbeddingModel` using SHA-256 token hashing, fixed dimensions, and L2 normalization.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: PASS for the embedding test.

### Task 2: Vector Index Writer Pipeline

**Files:**
- Create: `backend/app/rag/indexing.py`
- Modify: `backend/app/rag/__init__.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing test**

```python
def test_index_vector_documents_writes_embeddings() -> None:
    writer = RecordingVectorWriter()
    documents = [VectorDocument(document_id='chunk:1', text='Redis queue state', ...)]

    result = index_vector_documents(
        documents=documents,
        writer=writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
    )

    assert result.indexed_count == 1
    assert result.embedding_dimensions == 8
    assert result.document_ids == ['chunk:1']
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: FAIL until `backend.app.rag.indexing` exists.

- [x] **Step 3: Write minimal implementation**

Add `VectorIndexWriter`, `VectorIndexResult`, `PreviewVectorIndexWriter`, and `index_vector_documents`.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: PASS for indexing writer behavior.

### Task 3: RAG Corpus Collection

**Files:**
- Modify: `backend/app/rag/indexing.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing test**

```python
def test_build_rag_index_documents_includes_chunks_and_approved_knowledge(db_session: Session) -> None:
    chunk_id = seed_chunk(db_session, 'Redis queue state should be indexed for RAG.')
    approved = DecisionRecord(..., review_status='approved')
    pending = Todo(..., review_status='pending_review')

    documents = build_rag_index_documents(db_session)

    assert [document.document_id for document in documents] == [
        f'chunk:{chunk_id}',
        f'decision_record:{approved.id}',
    ]
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: FAIL until corpus collection exists.

- [x] **Step 3: Write minimal implementation**

Query all `DocumentChunk` rows and approved `DecisionRecord`, `HistoryEvent`, and `Todo` rows. Preserve `permission_level`, source URL, source snippet, source type, author, timestamp, and stable document ids.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: PASS for corpus collection.

### Task 4: Dry-Run Reindex API

**Files:**
- Create: `backend/app/api/v1/rag.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing test**

```python
def test_reindex_endpoint_returns_dry_run_index_summary(client: TestClient, db_session: Session) -> None:
    seed_chunk(db_session, 'Slack and Gmail history should be embedded for search.', 'gmail-api-index')

    response = client.post('/api/v1/rag/reindex')

    assert response.status_code == 200
    assert response.json()['indexed_count'] == 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: FAIL until the router and endpoint exist.

- [x] **Step 3: Write minimal implementation**

Add `POST /api/v1/rag/reindex` with `dry_run=True` default. Use deterministic embeddings and `PreviewVectorIndexWriter` so SQLite smoke can verify the pipeline without requiring live Postgres.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: all RAG indexing tests pass.

### Task 5: Verification and Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/portfolio-log.md`
- Create: `docs/superpowers/plans/2026-05-01-rag-vector-indexing.md`

- [x] **Step 1: Run backend tests**

Run: `uv run pytest backend/tests -v`

Expected: all backend tests pass.

- [x] **Step 2: Run frontend build**

Run: `npm.cmd run build` from `frontend`

Expected: Next.js build completes successfully.

- [x] **Step 3: Restart smoke server**

Run: `.\scripts\start-smoke.ps1 -DatabasePath '.tmp/paraworks-rag-vector-indexing.db'`

Expected: backend and frontend start on ports 8000 and 3000.

- [x] **Step 4: Smoke test reindex endpoint**

Run: `Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/rag/reindex'`

Expected: response includes `dry_run=true`, `storage_backend=preview`, and an `indexed_count` field.

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/embeddings.py backend/app/rag/indexing.py backend/app/api/v1/rag.py backend/app/api/v1/router.py backend/app/rag/__init__.py backend/tests/test_rag_indexing.py AGENTS.md docs/portfolio-log.md docs/superpowers/plans/2026-05-01-rag-vector-indexing.md
git commit -m "feat: add rag vector indexing pipeline"
```
