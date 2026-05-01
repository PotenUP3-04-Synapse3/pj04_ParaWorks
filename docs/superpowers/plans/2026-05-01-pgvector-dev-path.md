# pgvector Dev Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PostgreSQL + pgvector RAG path safe for developers to run without live OpenAI calls in automated tests.

**Architecture:** Document a manual live-provider path, add a PowerShell dev starter for Postgres/Redis-backed local runs, and add a skipped-by-default pgvector integration test that uses deterministic fake embeddings.

**Tech Stack:** Docker Compose, PowerShell, PostgreSQL + pgvector, SQLAlchemy, pytest.

---

### Task 1: Runbook and Script

**Files:**
- Create: `docs/superpowers/runbooks/pgvector-dev.md`
- Create: `scripts/start-pgvector-dev.ps1`
- Modify: `.env.example`
- Test: `backend/tests/test_pgvector_dev_runbook.py`

- [x] **Step 1: Write failing tests**

Verify the runbook documents `docker compose up -d postgres redis`, `OPENAI_API_KEY`, `dry_run=false`, `.env` secrecy, and `PARAWORKS_PGVECTOR_TEST_DATABASE_URL`. Verify the script starts Postgres/Redis, sets `DATABASE_URL`, runs DB init, and does not embed provider secrets.

- [x] **Step 2: Run tests to verify RED**

Run: `uv run pytest backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py -v`

Expected: FAIL because the runbook and script do not exist; integration test skips without env.

- [x] **Step 3: Implement runbook and script**

Add the pgvector dev runbook, PowerShell starter, and OpenAI embedding env examples.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py -v`

Expected: runbook tests pass and pgvector integration skips unless configured.

### Task 2: Fake Embedding pgvector Integration Test

**Files:**
- Create: `backend/tests/test_pgvector_integration.py`

- [x] **Step 1: Write skipped-by-default integration test**

Use `PARAWORKS_PGVECTOR_TEST_DATABASE_URL` to opt into a real pgvector database. Use `DeterministicHashEmbeddingModel`, not OpenAI.

- [x] **Step 2: Run test without env**

Expected: SKIPPED with a clear reason.

- [x] **Step 3: Attempt local Docker validation**

Run: `docker compose up -d postgres redis`

Observed: Docker pulled images, but Postgres could not bind `127.0.0.1:5432` because the port was unavailable/forbidden on this machine. Cleaned up with `docker compose down`.

### Task 3: Verification and Commit

- [x] **Step 1: Run focused tests**

Run: `uv run pytest backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py -v`

Expected: 2 pass, 1 skipped without pgvector env.

- [x] **Step 2: Run full backend tests**

Run: `uv run pytest backend/tests -v`

Expected: all backend tests pass, with pgvector integration skipped unless env is present.

- [x] **Step 3: Run frontend build**

Run: `npm.cmd run build` from `frontend`

Expected: Next.js build passes.

- [ ] **Step 4: Commit**

Run: `git commit -m "chore: document pgvector dev path"`
