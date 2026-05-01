# Incremental Vector Indexing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent unnecessary paid embedding calls by indexing only changed RAG documents.

**Architecture:** Store one vector indexing state row per `document_id + embedding_model`. Compute a stable content hash from the serving document fields; if the stored hash matches, skip embedding and vector writes while reporting saved embedding calls.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, PostgreSQL init SQL, deterministic local embeddings for smoke and tests.

---

### Task 1: Index State Model

**Files:**
- Create: `backend/app/models/vector_index.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/test_db_init.py`
- Create: `docker/postgres/init/003_vector_index_states.sql`

- [x] **Step 1: Write the failing test**

```python
def test_init_db_creates_expected_tables_on_fresh_engine() -> None:
    engine = create_engine('sqlite:///:memory:')

    init_db(engine_override=engine)

    tables = set(inspect(engine).get_table_names())
    assert {'sources', 'review_items', 'sync_jobs', 'agent_runs', 'vector_index_states'} <= tables
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`

Expected: FAIL because `VectorIndexState` and `vector_index_states` do not exist.

- [x] **Step 3: Write minimal implementation**

Add `VectorIndexState` with `document_id`, `embedding_model`, `embedding_dimensions`, `content_hash`, `status`, `last_error`, and `indexed_at`.

- [x] **Step 4: Run focused tests**

Run: `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`

Expected: PASS.

### Task 2: Content Hash and Incremental Indexing

**Files:**
- Modify: `backend/app/rag/indexing.py`
- Modify: `backend/app/rag/__init__.py`
- Modify: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing tests**

```python
def test_incremental_indexing_skips_unchanged_documents_after_success(db_session: Session) -> None:
    first_result = index_changed_vector_documents(...)
    second_result = index_changed_vector_documents(...)

    assert first_result.indexed_count == 1
    assert second_result.indexed_count == 0
    assert second_result.skipped_count == 1
    assert second_result.saved_embedding_calls == 1
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`

Expected: FAIL because `compute_vector_document_hash` and `index_changed_vector_documents` do not exist.

- [x] **Step 3: Write minimal implementation**

Add `compute_vector_document_hash` and `index_changed_vector_documents`. Persist successful hashes only after vector write succeeds.

- [x] **Step 4: Run focused tests**

Run: `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`

Expected: PASS.

### Task 3: Reindex API Cost Signals

**Files:**
- Modify: `backend/app/api/v1/rag.py`
- Modify: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing test**

```python
def test_reindex_endpoint_reports_skipped_documents_from_index_state(client: TestClient, db_session: Session) -> None:
    index_changed_vector_documents(...)

    response = client.post('/api/v1/rag/reindex')

    assert response.json()['indexed_count'] == 0
    assert response.json()['skipped_count'] == 1
    assert response.json()['saved_embedding_calls'] == 1
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`

Expected: FAIL until API uses incremental indexing.

- [x] **Step 3: Write minimal implementation**

Switch dry-run reindex to `index_changed_vector_documents(..., persist_state=False)` and return `skipped_count`, `skipped_document_ids`, and `saved_embedding_calls`.

- [x] **Step 4: Run focused tests**

Run: `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`

Expected: PASS.

### Task 4: Verification and Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/portfolio-log.md`
- Create: `docs/superpowers/plans/2026-05-01-incremental-vector-indexing.md`

- [x] **Step 1: Run backend tests**

Run: `uv run pytest backend/tests -v`

Expected: all backend tests pass.

- [x] **Step 2: Run focused lint**

Run: `uv run ruff check backend/app/models/vector_index.py backend/app/rag/indexing.py backend/app/api/v1/rag.py backend/tests/test_rag_indexing.py`

Expected: all checks pass.

- [x] **Step 3: Run frontend build**

Run: `npm.cmd run build` from `frontend`

Expected: Next.js build completes successfully.

- [x] **Step 4: Smoke test reindex API**

Run: `Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/rag/reindex'`

Expected: response includes `incremental=true`, `skipped_count`, and `saved_embedding_calls`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/vector_index.py backend/app/models/__init__.py backend/app/rag/indexing.py backend/app/rag/__init__.py backend/app/api/v1/rag.py backend/tests/test_rag_indexing.py backend/tests/test_db_init.py docker/postgres/init/003_vector_index_states.sql AGENTS.md docs/portfolio-log.md docs/superpowers/plans/2026-05-01-incremental-vector-indexing.md
git commit -m "feat: add incremental vector indexing"
```
