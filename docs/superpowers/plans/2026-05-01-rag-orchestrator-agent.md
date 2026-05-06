# RAG Orchestrator Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic RAG Orchestrator Agent slice that answers user questions from visible company evidence with citations, permission notices, and token/cost metadata.

**Architecture:** Keep this MVP cost-safe by reusing existing `DocumentChunk` storage and keyword retrieval instead of adding vector infrastructure in this step. The orchestrator has its own manifest and response contract, retrieves permission-filtered chunks for the current demo user, builds an evidence packet, and returns an answer with source links plus estimated token cost. Later, the retrieval implementation can be swapped for LangGraph + vector DB without changing the API response shape.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, existing permissions and agent runtime cost contracts.

---

## File Structure

- Create `backend/app/agents/rag_orchestrator_agent/__init__.py`
  - Export manifest, agent, deterministic model, service, and API response dataclasses.
- Create `backend/app/agents/rag_orchestrator_agent/agent.py`
  - Define manifest, model protocol, response dataclasses, deterministic model, and agent class.
- Create `backend/app/agents/rag_orchestrator_agent/service.py`
  - Retrieve matching chunks, apply permission filtering, build evidence packets, and run the agent.
- Create `backend/app/api/v1/ask.py`
  - Add `POST /api/v1/ask` endpoint.
- Modify `backend/app/api/v1/router.py`
  - Include ask router.
- Create `backend/app/schemas/ask.py`
  - Define `AskRequest`.
- Create `backend/tests/test_rag_orchestrator_agent.py`
  - Verify manifest and answer contract.
- Create `backend/tests/test_rag_orchestrator_service.py`
  - Verify retrieval, citations, and permission notices.
- Create `backend/tests/test_ask_api.py`
  - Verify end-to-end API behavior for admin and viewer users.
- Modify `docs/portfolio-log.md`
  - Record the RAG Orchestrator milestone.

## Task 1: Failing Tests

- [x] Add unit test for `RAG_ORCHESTRATOR_AGENT_MANIFEST`.
- [x] Add unit test for deterministic answer with source links and cost metadata.
- [x] Add service test that viewer cannot use restricted chunks and receives a permission notice.
- [x] Add API test for `/api/v1/ask`.

Run:

```powershell
uv run pytest backend/tests/test_rag_orchestrator_agent.py backend/tests/test_rag_orchestrator_service.py backend/tests/test_ask_api.py -v
```

Expected: fail because the RAG Orchestrator package and ask endpoint do not exist.

## Task 2: Implementation

- [x] Create RAG Orchestrator package.
- [x] Implement deterministic model and answer response contract.
- [x] Implement permission-aware retrieval service.
- [x] Add `/api/v1/ask` route and include it in the v1 router.

## Task 3: Verification and Commit

- [x] Run focused tests.
- [x] Run `uv run pytest backend/tests -v`.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: add rag orchestrator agent`.
