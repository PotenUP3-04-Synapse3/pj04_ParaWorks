# Mail Document Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Mail/Document Agent slice that turns Gmail and Drive evidence into reviewable company history candidates using the shared agent runtime contract.

**Architecture:** Mirror the Slack Agent boundary so each developer track can own one agent without inventing a separate integration style. The agent consumes an `EvidencePacket`, returns an `AgentRunResult`, persists an `AgentRun`, and creates linked `ReviewItem` rows. The initial model is deterministic to avoid paid LLM usage during MVP smoke testing.

**Tech Stack:** Python 3.12, SQLAlchemy, FastAPI, pytest, existing Agent Runtime contracts.

---

## File Structure

- Create `backend/app/agents/mail_document_agent/__init__.py`
  - Export the agent, deterministic model, manifest, and review bridge.
- Create `backend/app/agents/mail_document_agent/agent.py`
  - Define manifest, model protocol, deterministic model, and agent class.
- Create `backend/app/agents/mail_document_agent/service.py`
  - Build evidence packets from `gmail` and `drive` chunks.
  - Persist `AgentRun` and linked `ReviewItem` rows.
- Modify `backend/app/api/v1/integrations.py`
  - Add `POST /api/v1/integrations/mail-docs/agent-review`.
- Create `backend/tests/test_mail_document_agent.py`
  - Verify manifest and deterministic evidence-backed candidate behavior.
- Create `backend/tests/test_mail_document_agent_review_bridge.py`
  - Verify bridge filters Gmail/Drive, persists `AgentRun`, and links Review Items.
- Create `backend/tests/test_mail_document_agent_api.py`
  - Verify endpoint creates review candidates after Gmail/Drive sync.
- Modify `docs/portfolio-log.md`
  - Record the agent expansion and verification evidence.

## Task 1: Failing Tests

- [x] Add Mail/Document Agent unit tests for manifest and deterministic output.
- [x] Add bridge test that seeds Gmail, Drive, and Slack chunks and asserts only Gmail/Drive are included.
- [x] Add API test that syncs Gmail/Drive and runs `/mail-docs/agent-review`.

Run:

```powershell
uv run pytest backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py -v
```

Expected: fail because `backend.app.agents.mail_document_agent` and endpoint do not exist.

## Task 2: Implementation

- [x] Create Mail/Document Agent package.
- [x] Implement deterministic model with `MAIL_DOCUMENT_AGENT_MANIFEST`.
- [x] Implement `build_mail_document_evidence_packet`.
- [x] Implement `create_mail_document_agent_review_items`.
- [x] Add `/api/v1/integrations/mail-docs/agent-review`.

## Task 3: Verification and Commit

- [x] Run focused tests.
- [x] Run `uv run pytest backend/tests -v`.
- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: add mail document agent slice`.
