# Agent Run Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist agent run metadata so ParaWorks can audit token/cost usage, prompt versions, cache keys, and run status across Slack, Mail/Document, and RAG agents.

**Architecture:** Add a SQLAlchemy `AgentRun` model and export it through `backend.app.models`. Update the Slack Agent Review bridge to create one AgentRun per agent execution and link generated ReviewItems to that run through payload metadata. No API contract changes in this step.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, existing Agent Runtime contracts.

---

## File Structure

- Create `backend/app/models/agent_runs.py`
  - Add `AgentRun` table with agent name, prompt version, status, cache key,
    token usage, estimated cost, permission level, source window, and metadata.
- Modify `backend/app/models/__init__.py`
  - Export `AgentRun`.
- Modify `backend/app/agents/slack_agent/service.py`
  - Persist AgentRun before ReviewItems.
  - Store `agent_run_id` in each ReviewItem payload.
- Modify `backend/tests/test_db_init.py`
  - Assert `agent_runs` table is created.
- Create `backend/tests/test_agent_run_model.py`
  - Assert Slack bridge persists AgentRun metadata and links ReviewItem payload.
- Modify `docs/portfolio-log.md`
  - Record AgentRun/cost audit milestone.

## Task 1: Failing Tests

- [x] Add `agent_runs` to DB init expected tables.
- [x] Add a bridge test that seeds a Slack chunk, runs Slack Agent, then asserts:
  - one `AgentRun` row exists;
  - `agent_name == "slack_agent"`;
  - `prompt_version == "slack-timeline:v1"`;
  - token/cost fields are stored;
  - ReviewItem payload includes `agent_run_id`.

Run:

```powershell
uv run pytest backend/tests/test_agent_run_model.py backend/tests/test_db_init.py -v
```

Expected: fail because `AgentRun` and `agent_runs` do not exist.

## Task 2: Implementation

- [x] Create `AgentRun` model.
- [x] Export it in `backend/app/models/__init__.py`.
- [x] Update Slack Agent bridge to persist AgentRun.
- [x] Link ReviewItem payload to AgentRun id.

Run focused tests, then full backend tests.

## Task 3: Verification and Commit

- [x] Run `uv run pytest backend/tests -v`.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: persist agent run metadata`.
