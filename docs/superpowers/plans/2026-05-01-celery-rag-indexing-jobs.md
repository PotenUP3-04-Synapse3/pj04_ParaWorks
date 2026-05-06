# Celery RAG Indexing Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move RAG reindex jobs behind a Celery/Redis worker contract while keeping local smoke deterministic through eager execution.

**Architecture:** API creates `SyncJob(status='queued')`. In local/test eager mode, it executes the same task function immediately against the request DB session. In production worker mode, it enqueues `rag.reindex` on Redis; the worker updates `queued -> running -> complete/failed`.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, Redis, pytest.

---

### Task 1: Celery App and Task Contract

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/celery_app.py`
- Create: `backend/app/tasks/rag_indexing.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_rag_indexing_tasks.py`

- [x] **Step 1: Write failing tests**

Verify Celery uses Redis/eager settings and the RAG indexing executor moves a queued job to complete.

- [x] **Step 2: Run tests to verify RED**

Run: `uv run pytest backend/tests/test_rag_indexing_tasks.py -v`

Expected: FAIL because Celery task modules do not exist.

- [x] **Step 3: Implement Celery app and task executor**

Add `build_celery_app`, `run_rag_reindex_job`, `enqueue_rag_reindex_job`, and `execute_rag_reindex_job`.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_rag_indexing_tasks.py -v`

Expected: PASS.

### Task 2: API Queue Boundary and Job Polling

**Files:**
- Create: `backend/app/rag/reindexing.py`
- Modify: `backend/app/api/v1/rag.py`
- Modify: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write failing tests**

Verify `GET /api/v1/rag/reindex/jobs/{job_id}` returns job counters and missing jobs return 404.

- [x] **Step 2: Run tests to verify RED**

Run focused tests for the new job detail endpoint.

- [x] **Step 3: Implement API changes**

Move reindex logic to `backend/app/rag/reindexing.py`; make job creation queue-first; keep eager mode complete for local smoke.

- [x] **Step 4: Verify GREEN**

Run focused RAG indexing tests.

### Task 3: Worker Script and Docs

**Files:**
- Create: `scripts/start-celery-worker.ps1`
- Modify: `.env.example`
- Modify: `docs/superpowers/runbooks/pgvector-dev.md`
- Test: `backend/tests/test_rag_indexing_tasks.py`

- [x] **Step 1: Write failing test**

Verify the worker script disables eager mode and starts Celery with `--pool=solo`.

- [x] **Step 2: Run test to verify RED**

Expected: FAIL because the worker script does not exist.

- [x] **Step 3: Implement script and docs**

Add `start-celery-worker.ps1`, document worker mode, and add `CELERY_TASK_ALWAYS_EAGER=true` to `.env.example`.

### Task 4: Verification and Commit

- [x] **Step 1: Run focused tests**

Run: `uv run pytest backend/tests/test_rag_indexing_tasks.py backend/tests/test_rag_indexing.py -v`

- [x] **Step 2: Run full backend tests**

Run: `uv run pytest backend/tests -v`

- [x] **Step 3: Run frontend build**

Run: `npm.cmd run build` from `frontend`

- [x] **Step 4: Smoke test**

Restart SQLite smoke, run sync + reindex job + job detail + summary checks.

- [ ] **Step 5: Commit**

Run: `git commit -m "feat: queue rag indexing jobs with celery"`
