# Playwright And RAG Permission Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repeatable Playwright visual checks available and strengthen the first RAG permission-audit slice.

**Architecture:** Add Playwright as a frontend dev tool with a repo-level smoke runner that can reuse or start local smoke servers. Add permission-safe search metadata (`hidden_match_count`, `source_id`) and preserve connector ACL metadata on ingested chunks so RAG and Review flows can be audited without exposing hidden source content.

**Tech Stack:** Playwright, Next.js, FastAPI, SQLAlchemy, pytest, existing ParaWorks smoke scripts.

---

### Task 1: Playwright Visual Smoke

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/visual-smoke.spec.ts`
- Create: `scripts/run-visual-smoke.ps1`
- Modify: `.gitignore`

- [x] Install `@playwright/test`.
- [x] Add `npm run test:visual`.
- [x] Add desktop/mobile Chromium visual smoke checks for dashboard, integrations, agent-runs, and search.
- [x] Add a repo wrapper that starts or reuses smoke servers, seeds demo data, and runs Playwright.
- [x] Ignore Playwright reports and test results.

### Task 2: Korean Dashboard Cleanup

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

- [x] Replace mojibake text with readable Korean copy.
- [x] Keep dashboard density and Admin cost context consistent with the existing UI.

### Task 3: RAG Permission-Audit Contract

**Files:**
- Modify: `backend/tests/test_search_permissions.py`
- Modify: `backend/tests/test_connector_ingestion_contract.py`
- Modify: `backend/tests/test_ask_api.py`
- Modify: `backend/app/agent_runtime/contracts.py`
- Modify: `backend/app/agents/rag_orchestrator_agent/agent.py`
- Modify: `backend/app/api/v1/ask.py`
- Modify: `backend/app/ingestion/service.py`
- Modify: `backend/app/api/v1/search.py`
- Modify: `frontend/src/app/search/page.tsx`
- Modify: `frontend/src/lib/api/types.ts`

- [x] Write failing tests for `hidden_match_count`, visible `source_id`, and preserved connector ACL metadata.
- [x] Add `hidden_match_count` to search responses.
- [x] Add visible `source_id` to search results.
- [x] Preserve source id, permission level, participants, and connector raw metadata in chunk metadata.
- [x] Surface hidden count and source id in the search UI without leaking hidden content.
- [x] Add `source_ids` to Ask/RAG answers so answer citations can be audited without exposing hidden matches.

### Task 4: Verification And Record

**Files:**
- Modify: `docs/portfolio-log.md`

- [x] Run focused pytest and Ruff.
- [x] Run full backend pytest.
- [x] Run frontend build.
- [x] Run Playwright visual smoke.
- [x] Record portfolio and cost/security notes.
