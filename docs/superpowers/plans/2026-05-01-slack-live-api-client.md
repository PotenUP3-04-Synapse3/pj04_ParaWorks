# Slack Live API Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first live OAuth connector slice by implementing a Slack Web API client boundary without using real Slack tokens in tests.

**Architecture:** Keep `SlackConnector` responsible for mapping Slack message payloads into `SourceEvent`. Add `SlackWebApiClient` behind the existing `SlackApiClient` protocol, then add a settings-based connector factory that uses live Slack only when bot token and channel ids are configured. Mock mode remains the default.

**Tech Stack:** FastAPI settings, httpx, pytest fake transports, existing connector ingestion contract.

---

### Task 1: Slack Web API Client Contract

**Files:**
- Modify: `backend/tests/test_slack_connector.py`
- Modify: `backend/app/connectors/slack.py`

- [x] Write RED tests for `conversations.history` bearer-token calls.
- [x] Write RED tests for cursor pagination.
- [x] Write RED tests for Slack API error handling.
- [x] Implement `SlackWebApiClient` and `SlackApiError`.

### Task 2: Configured Connector Factory

**Files:**
- Create: `backend/tests/test_connector_factory.py`
- Create: `backend/app/connectors/factory.py`
- Modify: `backend/app/api/v1/integrations.py`

- [x] Write RED tests that missing Slack settings keep mock mode.
- [x] Write RED tests that Slack token/channel settings build a live `SlackConnector`.
- [x] Update the sync endpoint to use the factory.
- [x] Preserve mock/demo behavior when settings are empty.

### Task 3: Documentation And Verification

**Files:**
- Modify: `docs/superpowers/runbooks/slack-integration.md`
- Modify: `docs/portfolio-log.md`

- [x] Document live Slack env settings, no-secret policy, and fake-client tests.
- [x] Run focused pytest and Ruff.
- [x] Run full backend pytest.
- [x] Run frontend build and Playwright visual smoke.
