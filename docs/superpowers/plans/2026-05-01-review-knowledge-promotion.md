# Review Knowledge Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote approved Review Queue items into durable knowledge tables so ParaWorks closes the source evidence -> agent candidate -> human approval -> company memory loop.

**Architecture:** Add a focused promotion service used by the existing review approval endpoint. The service maps `decision_record`, `history_event`, and `todo` Review Items into `DecisionRecord`, `HistoryEvent`, and `Todo` rows while preserving source links, snippets, confidence, permission, and approved review status.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, existing ReviewItem and knowledge models.

---

## Task 1: Failing Tests

- [x] Add review API tests that approve a decision, history event, and todo Review Item.
- [x] Assert a corresponding durable knowledge row is created.
- [x] Assert source evidence, confidence, permission, and `review_status='approved'` are preserved.

Run:

```powershell
uv run pytest backend/tests/test_review_knowledge_promotion.py -v
```

Expected: fail because approval currently only changes ReviewItem status.

## Task 2: Implementation

- [x] Create `backend/app/knowledge/promotion.py`.
- [x] Map `decision_record` payloads to `DecisionRecord`.
- [x] Map `history_event` payloads to `HistoryEvent`.
- [x] Map `todo` payloads to `Todo`.
- [x] Call promotion service from `approve_review_item`.

## Task 3: Verification and Commit

- [x] Run focused promotion tests.
- [x] Run `uv run pytest backend/tests -v`.
- [x] Smoke approve an item and verify dashboard/review remain reachable.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: promote approved review items`.
