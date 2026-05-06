# Review Vector LangGraph Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement MVP foundations for the next three product steps: Review Queue hardening, vector-ready RAG, and LangGraph-ready orchestration.

**Architecture:** Keep each foundation independently testable. Review Queue validation lives beside promotion logic, vector retrieval is a replaceable RAG package, and orchestration is a local workflow contract that can later be backed by LangGraph `StateGraph`.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js, TypeScript, Tailwind CSS, optional future LangGraph.

---

### Task 1: Review Queue Promotion Preview

**Files:**
- Modify: `backend/tests/test_review.py`
- Modify: `backend/app/knowledge/promotion.py`
- Modify: `backend/app/api/v1/review.py`
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/review/page.tsx`

- [x] **Step 1: Write failing backend tests**

Add tests proving:

- `GET /api/v1/review/{id}/promotion-preview` returns normalized promoted shape.
- approving a promotable item with missing required fields returns 400.

- [x] **Step 2: Verify RED**

Run:

`uv run pytest backend/tests/test_review.py::test_review_item_preview_returns_promotion_shape backend/tests/test_review.py::test_approve_review_item_rejects_missing_required_fields -v`

Expected: endpoint missing and approval too permissive.

- [x] **Step 3: Implement shared preview/validation**

Add:

- `build_promotion_preview`
- `validate_review_item_for_approval`
- normalized payload helpers for `decision_record`, `history_event`, and `todo`

- [x] **Step 4: Expose frontend preview**

Fetch promotion previews for pending review items and show target type, normalized fields, missing fields, and approval availability.

### Task 2: Vector-Ready RAG Foundation

**Files:**
- Create: `backend/tests/test_vector_retriever.py`
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/vector_store.py`
- Modify: `backend/app/agents/rag_orchestrator_agent/service.py`

- [x] **Step 1: Write failing vector store tests**

Add tests for permission-aware ranking, hidden match counting, export shape, and RAG candidate projection.

- [x] **Step 2: Verify RED**

Run: `uv run pytest backend/tests/test_vector_retriever.py -v`

Expected: missing module/import failure.

- [x] **Step 3: Implement in-memory vector store contract**

Add `VectorDocument`, `VectorMatch`, `VectorSearchResult`, `VectorStore`, and deterministic `InMemoryVectorStore`.

- [x] **Step 4: Bridge current RAG candidates**

Add `vector_documents_from_candidates` so existing keyword candidates can be projected into future vector indexes.

### Task 3: LangGraph-Ready Orchestration Skeleton

**Files:**
- Create: `backend/tests/test_agent_orchestration.py`
- Create: `backend/app/agent_runtime/orchestration.py`
- Modify: `backend/app/agent_runtime/__init__.py`

- [x] **Step 1: Write failing orchestration tests**

Add tests proving the local workflow runs nodes in this order:

1. `collect_evidence`
2. `draft_review_candidates`
3. `retrieve_company_memory`
4. `answer_with_rag`

- [x] **Step 2: Verify RED**

Run: `uv run pytest backend/tests/test_agent_orchestration.py -v`

Expected: missing orchestration module.

- [x] **Step 3: Implement append-only workflow state**

Add immutable `AgentWorkflowState`, `AgentWorkflow`, and `build_company_memory_workflow`.

### Task 4: Verification and Commit

- [x] **Step 1: Run focused tests**

Run:

- `uv run pytest backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -v`
- `uv run pytest backend/tests/test_vector_retriever.py backend/tests/test_rag_orchestrator_service.py -v`
- `uv run pytest backend/tests/test_agent_orchestration.py -v`
- `npm.cmd run build`

- [x] **Step 2: Run full verification**

Run:

- `uv run pytest backend/tests -v`
- `npm.cmd run build`
- smoke HTTP and browser checks for `/review`, `/search`, and `/agent-runs`

- [x] **Step 3: Commit**

Commit message: `feat: add review vector orchestration foundations`
