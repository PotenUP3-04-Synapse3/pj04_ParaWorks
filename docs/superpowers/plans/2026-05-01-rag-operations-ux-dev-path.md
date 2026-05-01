# RAG Operations UX And Dev Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve RAG indexing operations UX, user-facing search freshness UX, Celery queue validation, and pgvector local development resilience.

**Architecture:** Keep technical indexing and cost counters in Admin operations while giving normal search users a non-technical company-memory freshness signal. Preserve the current backend API shape but add small job-summary fields and tests for queue/failure behavior. Make the Docker pgvector path configurable through environment-backed port settings.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, Redis, PostgreSQL + pgvector, Next.js, React, Tailwind CSS.

---

### Task 1: Backend Job Summary Contract

**Files:**
- Modify: `backend/tests/test_rag_indexing.py`
- Modify: `backend/app/api/v1/rag.py`

- [x] Write a failing API test that a failed RAG indexing job returns a `failure_reason`.
- [x] Write a failing API test that non-eager `/api/v1/rag/reindex/jobs` returns `queued` and calls the enqueue boundary without running the job.
- [x] Implement minimal `_job_summary` changes and keep existing job fields stable.
- [x] Run the focused RAG tests.

### Task 2: pgvector Port Conflict Path

**Files:**
- Modify: `backend/tests/test_rag_indexing_tasks.py`
- Modify: `docker-compose.yml`
- Modify: `scripts/start-pgvector-dev.ps1`
- Modify: `docs/superpowers/runbooks/pgvector-dev.md`

- [x] Write a failing script/compose assertion for configurable Postgres and Redis ports.
- [x] Update compose to use `PARAWORKS_POSTGRES_PORT` and `PARAWORKS_REDIS_PORT` defaults.
- [x] Update the helper script to accept `-PostgresPort` and `-RedisPort`.
- [x] Document the alternate-port command.

### Task 3: Admin RAG Operations UX

**Files:**
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/agent-runs/page.tsx`

- [x] Add frontend types for `failure_reason`.
- [x] Replace broken Korean copy with readable Korean operations copy.
- [x] Show latest job status, progress, failure reason, updated time, and a compact latest-job list.
- [x] Keep embedding-cost counters visible only in Admin operations.

### Task 4: Search User UX

**Files:**
- Modify: `frontend/src/app/search/page.tsx`

- [x] Fetch RAG indexing summary on the search page.
- [x] Show a non-technical company-memory freshness panel.
- [x] Remove token/cost/cache technical counters from the normal user answer area.
- [x] Keep permission and evidence signals visible.

### Task 5: Verification And Record

**Files:**
- Modify: `docs/portfolio-log.md`

- [x] Run focused pytest and Ruff for changed backend files.
- [x] Run full backend pytest if focused tests pass.
- [x] Run frontend build.
- [x] Smoke-check `/agent-runs`, `/search`, and relevant RAG APIs.
- [x] Record the implementation and cost-aware choices in `docs/portfolio-log.md`.
