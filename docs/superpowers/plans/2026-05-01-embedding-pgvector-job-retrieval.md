# Embedding Provider, pgvector Write, Job, and Retrieval Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the next RAG infrastructure slice in the order 5 -> 6 -> 8 -> 7: embedding provider boundary, pgvector write mode, indexing job contract, and vector-capable retrieval.

**Architecture:** Keep all paid provider calls behind `EmbeddingModel.embed_many`, run incremental skip checks before embedding, write production vectors only through `PgVectorStore`, expose a job API using existing `SyncJob`, and let Ask use vector retrieval only when explicitly enabled.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, httpx, OpenAI Embeddings API, PostgreSQL + pgvector.

---

### Task 5: Embedding Provider Boundary

**Files:**
- Modify: `backend/app/rag/embeddings.py`
- Modify: `backend/app/rag/indexing.py`
- Modify: `backend/app/rag/__init__.py`
- Test: `backend/tests/test_embedding_provider.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write failing tests**

Verify that OpenAI embedding requests batch inputs, include `dimensions`, preserve response order by `index`, and return usage metadata. Verify that incremental indexing calls `embed_many` only for changed documents.

- [x] **Step 2: Run tests to verify RED**

Run: `uv run pytest backend/tests/test_embedding_provider.py backend/tests/test_rag_indexing.py -v`

Expected: FAIL because OpenAI provider classes and `EmbeddingBatchResult` do not exist.

- [x] **Step 3: Implement provider boundary**

Add `EmbeddingBatchResult`, `OpenAIEmbeddingConfig`, `OpenAIEmbeddingModel`, and deterministic `embed_many`. Update incremental indexing to batch changed documents after skip checks.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_embedding_provider.py backend/tests/test_rag_indexing.py -v`

Expected: PASS.

### Task 6: pgvector Write Mode

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/v1/rag.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write failing tests**

Verify `/api/v1/rag/reindex?dry_run=false` rejects SQLite with a clear 400 instead of silently pretending to write vectors.

- [x] **Step 2: Run tests to verify RED**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: FAIL because the route still returns 501 and dry-run responses do not expose embedding request metrics.

- [x] **Step 3: Implement pgvector path**

Add OpenAI embedding settings. Keep dry-run on deterministic preview. For `dry_run=false`, require PostgreSQL and `OPENAI_API_KEY`, ensure pgvector schema, use `PgVectorStore`, and persist vector index state.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_rag_indexing.py -v`

Expected: PASS.

### Task 8: Indexing Job Contract

**Files:**
- Modify: `backend/app/api/v1/rag.py`
- Test: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write failing test**

Verify `POST /api/v1/rag/reindex/jobs` records a `SyncJob` with `connector_type='rag-index'`, completes the index run, and returns cost counters.

- [x] **Step 2: Run test to verify RED**

Run: `uv run pytest backend/tests/test_rag_indexing.py::test_reindex_job_endpoint_records_indexing_job -v`

Expected: FAIL with 404.

- [x] **Step 3: Implement job endpoint**

Create a `SyncJob`, execute the shared reindex runner, update status/progress/message, and return the job id with index summary.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_rag_indexing.py::test_reindex_job_endpoint_records_indexing_job -v`

Expected: PASS.

### Task 7: Vector-Capable RAG Retrieval

**Files:**
- Modify: `backend/app/agents/rag_orchestrator_agent/service.py`
- Modify: `backend/app/api/v1/ask.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_rag_orchestrator_service.py`

- [x] **Step 1: Write failing test**

Verify `answer_question_with_rag(..., vector_store=...)` can answer from vector matches without DB keyword candidates.

- [x] **Step 2: Run test to verify RED**

Run: `uv run pytest backend/tests/test_rag_orchestrator_service.py::test_rag_service_can_answer_from_vector_store_matches -v`

Expected: FAIL because `answer_question_with_rag` does not accept `vector_store`.

- [x] **Step 3: Implement vector retrieval path**

Add optional vector store retrieval, convert vector matches to `RagEvidenceCandidate`, and add `rag_use_pgvector_search` feature flag for Ask API pgvector search.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_rag_orchestrator_service.py::test_rag_service_can_answer_from_vector_store_matches -v`

Expected: PASS.

### Task 9: Verification and Commit

- [x] **Step 1: Run full backend tests**

Run: `uv run pytest backend/tests -v`

Expected: all backend tests pass.

- [x] **Step 2: Run focused Ruff**

Run: `uv run ruff check backend/app/rag/embeddings.py backend/app/rag/indexing.py backend/app/api/v1/rag.py backend/app/api/v1/ask.py backend/app/agents/rag_orchestrator_agent/service.py backend/tests/test_embedding_provider.py backend/tests/test_rag_indexing.py backend/tests/test_rag_orchestrator_service.py`

Expected: all checks pass.

- [x] **Step 3: Run frontend build**

Run: `npm.cmd run build` from `frontend`

Expected: Next.js build succeeds.

- [x] **Step 4: Smoke test**

Run Slack/Gmail sync, `POST /api/v1/rag/reindex/jobs`, and HTTP checks for `/search`, `/dashboard`, `/review`.

Expected: all return 200 and the reindex job returns cost counters.

- [ ] **Step 5: Commit**

Run: `git commit -m "feat: add embedding provider and vector retrieval path"`
