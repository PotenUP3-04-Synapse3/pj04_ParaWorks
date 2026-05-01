# Agent Run Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose agent execution cost and token metadata through an API and dashboard panel so ParaWorks can demonstrate auditable AI cost governance.

**Architecture:** Add a read-only `/api/v1/agent-runs` endpoint over the existing `AgentRun` table. The endpoint returns recent runs plus aggregate count, token total, and estimated cost. The dashboard fetches this endpoint server-side and renders a compact Agent Cost panel alongside existing source and sync metrics.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, Next.js 15, TypeScript, Tailwind.

---

## Task 1: Backend API Tests

- [x] Create `backend/tests/test_agent_runs_api.py`.
- [x] Seed two `AgentRun` rows.
- [x] Assert `/api/v1/agent-runs` returns:
  - `total_runs == 2`;
  - summed `total_tokens`;
  - summed `estimated_cost_usd`;
  - recent runs ordered by newest id;
  - run fields needed by the dashboard.

Run:

```powershell
uv run pytest backend/tests/test_agent_runs_api.py -v
```

Expected: fail because `/api/v1/agent-runs` does not exist.

## Task 2: Backend Implementation

- [x] Create `backend/app/api/v1/agent_runs.py`.
- [x] Add route to `backend/app/api/v1/router.py`.
- [x] Keep response shape read-only and stable for frontend use.

## Task 3: Dashboard UI

- [x] Add `AgentRunsResponse` and `AgentRunSummaryItem` types.
- [x] Fetch `/api/v1/agent-runs` from `frontend/src/app/dashboard/page.tsx`.
- [x] Add cost/token summary stat.
- [x] Add recent Agent Runs panel with agent name, status, tokens, cost, prompt version, and permission.

## Task 4: Verification and Commit

- [x] Run focused backend test.
- [x] Run `uv run pytest backend/tests -v`.
- [x] Run `npm.cmd run build`.
- [x] Restart smoke server and verify `/dashboard`, `/api/v1/agent-runs`, and a seeded agent run flow.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: add agent run observability`.
