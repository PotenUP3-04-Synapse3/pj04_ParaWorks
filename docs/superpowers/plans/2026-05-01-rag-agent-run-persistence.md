# RAG Agent Run Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every RAG Orchestrator ask execution as an `AgentRun` so dashboard cost observability covers all three agent tracks.

**Architecture:** Keep the public `/api/v1/ask` response unchanged. Update the RAG Orchestrator service to create one `AgentRun` row after producing a `RagAnswer`, storing prompt version, cache key, model, tokens, cost, permission, question, source count, and hidden match count. Existing `/api/v1/agent-runs` will automatically include these runs.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, existing AgentRun model and RAG Orchestrator service.

---

## Task 1: Failing Test

- [x] Add a service-level test that seeds a visible chunk, calls `answer_question_with_rag`, and asserts:
  - one `AgentRun` row exists;
  - `agent_name == "rag_orchestrator_agent"`;
  - `prompt_version == "rag-answer:v1"`;
  - token and cost fields match the answer cost;
  - metadata records question, source count, and hidden match count.

Run:

```powershell
uv run pytest backend/tests/test_rag_orchestrator_service.py -v
```

Expected: fail because RAG asks are not persisted as `AgentRun` rows yet.

## Task 2: Implementation

- [x] Import `AgentRun` in `backend/app/agents/rag_orchestrator_agent/service.py`.
- [x] Persist one AgentRun after `selected_agent.answer(...)`.
- [x] Commit the DB transaction and return the existing `RagAnswer`.

## Task 3: Verification and Commit

- [x] Run focused RAG service tests.
- [x] Run `uv run pytest backend/tests -v`.
- [x] Smoke run `/api/v1/ask` and `/api/v1/agent-runs`.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: persist rag agent runs`.
