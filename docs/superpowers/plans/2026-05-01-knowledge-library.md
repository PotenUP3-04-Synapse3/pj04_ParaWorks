# Knowledge Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose approved decisions, history events, and todos through a Knowledge Library API and page so users can inspect durable company memory after Review approval.

**Architecture:** Add a read-only `/api/v1/knowledge` endpoint that returns the three existing knowledge tables in a stable response shape. Add a `/knowledge` frontend page and navigation item that renders counts and evidence-preserving lists for decisions, history, and tasks.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, Next.js 15, TypeScript, Tailwind.

---

## Task 1: Backend API Tests

- [x] Create `backend/tests/test_knowledge_api.py`.
- [x] Seed `DecisionRecord`, `HistoryEvent`, and `Todo`.
- [x] Assert `GET /api/v1/knowledge` returns all three sections, counts, evidence, permission, confidence, and review status.

Expected RED:

```powershell
uv run pytest backend/tests/test_knowledge_api.py -v
```

The endpoint should initially return 404.

## Task 2: Backend Implementation

- [x] Create `backend/app/api/v1/knowledge.py`.
- [x] Include the router in `backend/app/api/v1/router.py`.
- [x] Return decisions, history events, todos, and aggregate counts.

## Task 3: Frontend Knowledge Page

- [x] Add frontend `KnowledgeResponse` types.
- [x] Add `/knowledge` page.
- [x] Add Knowledge navigation labels in Korean and English.
- [x] Add Knowledge item to the app shell navigation.

## Task 4: Verification and Commit

- [x] Run focused backend tests.
- [x] Run full backend tests.
- [x] Run frontend build.
- [x] Smoke `/knowledge`, `/review`, `/dashboard`, and approval flow.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: add knowledge library`.
