# RAG Indexing Observability UI Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show RAG indexing cost-control signals in the Admin/Agent Operations surface without cluttering the end-user Search experience.

**Architecture:** Add a read-only RAG indexing summary API that reports latest indexing jobs and vector index state counts. Render those metrics on `/agent-runs` as an admin observability panel, leaving `/search` focused on business user retrieval.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js server components, Tailwind CSS, lucide-react.

---

### Task 1: RAG Indexing Summary API

**Files:**
- Modify: `backend/app/api/v1/rag.py`
- Modify: `backend/tests/test_rag_indexing.py`

- [x] **Step 1: Write the failing test**

```python
def test_rag_indexing_summary_returns_latest_jobs_and_state_counts(client, db_session):
    client.post('/api/v1/rag/reindex/jobs')

    response = client.get('/api/v1/rag/indexing/summary')

    assert response.status_code == 200
    assert response.json()['latest_jobs'][0]['connector_type'] == 'rag-index'
```

- [x] **Step 2: Run test to verify RED**

Run: `uv run pytest backend/tests/test_rag_indexing.py::test_rag_indexing_summary_returns_latest_jobs_and_state_counts -v`

Expected: FAIL with 404.

- [x] **Step 3: Implement minimal API**

Add `GET /api/v1/rag/indexing/summary`, aggregate `VectorIndexState.status`, fetch latest `rag-index` jobs, and parse job counters from message text.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_rag_indexing.py::test_rag_indexing_summary_returns_latest_jobs_and_state_counts -v`

Expected: PASS.

### Task 2: Admin Observability Panel

**Files:**
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/agent-runs/page.tsx`

- [x] **Step 1: Add API types**

Add `RagIndexingJobSummary` and `RagIndexingSummaryResponse`.

- [x] **Step 2: Render the panel**

Fetch `/api/v1/rag/indexing/summary` in `/agent-runs` and show indexed state count, latest skipped count, saved embedding calls, and latest job detail.

- [x] **Step 3: Verify build**

Run: `npm.cmd run build` from `frontend`.

Expected: PASS.

### Task 3: Verification and Commit

- [x] **Step 1: Run backend tests**

Run: `uv run pytest backend/tests -v`

Expected: all backend tests pass.

- [x] **Step 2: Run frontend build**

Run: `npm.cmd run build` from `frontend`

Expected: Next.js build succeeds.

- [x] **Step 3: Smoke test**

Restart smoke, run Slack/Gmail sync, run `POST /api/v1/rag/reindex/jobs`, verify `GET /api/v1/rag/indexing/summary`, and check `/agent-runs` HTTP 200.

- [ ] **Step 4: Commit**

Run: `git commit -m "feat: show rag indexing observability"`
