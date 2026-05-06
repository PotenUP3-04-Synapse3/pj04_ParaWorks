# Agent Run Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AgentRun operations page that summarizes AI execution cost, token usage, cache behavior, and per-agent totals.

**Architecture:** Extend the existing AgentRun API with a read-only summary endpoint that aggregates persisted `AgentRun` rows. Add a frontend `/agent-runs` page that consumes the summary and existing recent-run list, then links each row to `/agent-runs/[id]`.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js App Router, TypeScript, Tailwind CSS, lucide-react.

---

### Task 1: Backend Summary API

**Files:**
- Modify: `backend/tests/test_agent_runs_api.py`
- Modify: `backend/app/api/v1/agent_runs.py`

- [x] **Step 1: Write the failing test**

Add `test_agent_run_summary_api_returns_cost_and_agent_breakdown` that creates Slack, Mail/Docs, and RAG runs, then asserts:

- `GET /api/v1/agent-runs/summary` returns 200.
- Totals include run count, token count, cost, average tokens, average cost, cache hits, and cache hit rate.
- `by_agent` contains one row per agent with run count, token total, cost total, average tokens, latest run id, and latest status.
- `by_status` counts `complete` and `failed`.

- [x] **Step 2: Verify RED**

Run: `uv run pytest backend/tests/test_agent_runs_api.py::test_agent_run_summary_api_returns_cost_and_agent_breakdown -v`

Expected: 404 because the summary endpoint does not exist.

- [x] **Step 3: Implement the endpoint**

Add `@router.get('/summary')` before `@router.get('/{run_id}')`, aggregate rows in Python from `select(AgentRun).order_by(AgentRun.id.desc())`, and round cost fields to six decimals.

- [x] **Step 4: Verify GREEN**

Run: `uv run pytest backend/tests/test_agent_runs_api.py -v`

Expected: all AgentRun API tests pass.

### Task 2: Frontend AgentRun Operations Page

**Files:**
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/lib/i18n/dictionary.ts`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/agent-runs/page.tsx`

- [x] **Step 1: Add API types**

Add `AgentRunSummaryResponse` and `AgentRunAgentSummary` types matching the new backend response.

- [x] **Step 2: Add navigation**

Add an Agent Runs navigation item with Korean label `AI 실행` and English label `AI Runs`.

- [x] **Step 3: Add the page**

Create `/agent-runs` with summary cards, per-agent cost table, status counts, recent run list, and links to each run detail page.

- [x] **Step 4: Link dashboard to the page**

Add a compact link from the dashboard AgentRun panel to `/agent-runs`.

- [x] **Step 5: Verify frontend build**

Run: `npm.cmd run build` from `frontend`.

Expected: build succeeds and includes `/agent-runs`.

### Task 3: Portfolio Log, Smoke Test, Commit

**Files:**
- Modify: `docs/portfolio-log.md`

- [x] **Step 1: Update portfolio log**

Add an observability entry describing the AgentRun operations page and summary endpoint.

- [x] **Step 2: Run full verification**

Run:

- `uv run pytest backend/tests -v`
- `npm.cmd run build`
- smoke HTTP checks for `/health`, `/agent-runs`, `/agent-runs/summary`, and `/dashboard`
- browser check for `/agent-runs`

- [x] **Step 3: Commit**

Commit message: `feat: add agent run operations summary`
