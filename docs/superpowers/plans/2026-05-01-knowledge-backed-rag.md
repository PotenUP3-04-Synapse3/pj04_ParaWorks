# Knowledge Backed RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the RAG Orchestrator answer from approved company memory records, not only raw document chunks.

**Architecture:** Extend the deterministic MVP retrieval layer to collect matching `DecisionRecord`, `HistoryEvent`, and `Todo` rows as `EvidenceMessage` objects. Keep permission filtering, hidden match notices, source links, source snippets, and AgentRun persistence unchanged from the public API perspective.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, existing RAG Orchestrator contracts.

---

## Task 1: Failing Tests

- [x] Add a service test where only an approved `DecisionRecord` exists and `/ask` can answer from it.
- [x] Add an API test where only approved knowledge exists and `/api/v1/ask` returns the knowledge source link.
- [x] Add a restricted approved knowledge test for viewer hidden match behavior.

Expected RED:

```powershell
uv run pytest backend/tests/test_rag_orchestrator_service.py backend/tests/test_ask_api.py -v
```

The tests should fail because RAG retrieval currently only reads `DocumentChunk`.

## Task 2: Implementation

- [x] Add a small `RagEvidenceCandidate` dataclass.
- [x] Convert raw chunks and approved knowledge records into common evidence candidates.
- [x] Apply permission filtering to both candidate types.
- [x] Build the `EvidencePacket` from visible candidates.

## Task 3: Verification and Commit

- [x] Run focused RAG/Ask tests.
- [x] Run `uv run pytest backend/tests -v`.
- [x] Smoke approve Review Items and ask from approved knowledge.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: use approved knowledge in rag`.
