# Agent Run Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AgentRun detail API and page so individual AI executions can be audited beyond dashboard summaries.

**Architecture:** Extend the existing read-only AgentRun API with `GET /api/v1/agent-runs/{run_id}`. Reuse the same serialized fields as the list endpoint, then add a frontend `/agent-runs/[id]` page and link dashboard recent runs to it.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, Next.js 15, TypeScript, Tailwind.

---

## Task 1: Backend RED

- [x] Add test for `GET /api/v1/agent-runs/{id}` returning all run fields.
- [x] Add test for missing id returning 404.

Expected RED:

```powershell
uv run pytest backend/tests/test_agent_runs_api.py -v
```

The detail endpoint should initially return 404.

## Task 2: Backend Implementation

- [x] Add shared serializer in `backend/app/api/v1/agent_runs.py`.
- [x] Add detail route by id.
- [x] Preserve list response shape.

## Task 3: Frontend Detail Page

- [x] Reuse `AgentRunSummaryItem` as detail type.
- [x] Add `/agent-runs/[id]` page.
- [x] Link dashboard recent runs to detail page.
- [x] Render prompt, model, cache key, token split, cost, permission, source window, timestamps, and metadata.

## Task 4: Verification and Commit

- [x] Run focused backend tests.
- [x] Run full backend tests.
- [x] Run frontend build.
- [x] Smoke run an agent, open `/agent-runs/{id}`, `/dashboard`, and `/review`.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: add agent run detail view`.
