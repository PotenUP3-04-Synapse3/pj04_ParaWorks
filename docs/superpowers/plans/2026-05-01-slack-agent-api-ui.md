# Slack Agent API and UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Slack Agent Review bridge through a backend API and a frontend Tools action so users can generate AI-style Review candidates from synced Slack evidence.

**Architecture:** Keep the bridge service isolated under `backend/app/agents/slack_agent/`. Add a deterministic demo model that behaves like the future LLM boundary without live API calls. Add `POST /api/v1/integrations/slack/agent-review`, then wire a button on `/integrations`.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js 15, React 19, Tailwind CSS.

---

## File Structure

- Modify `backend/app/agents/slack_agent/agent.py`
  - Add `DeterministicSlackAgentModel` for demo/local smoke.
- Modify `backend/app/agents/slack_agent/__init__.py`
  - Re-export `DeterministicSlackAgentModel`.
- Modify `backend/app/api/v1/integrations.py`
  - Add `POST /slack/agent-review`.
- Create `backend/tests/test_slack_agent_api.py`
  - Verify sync plus agent review creates an agent-backed ReviewItem.
- Modify `frontend/src/lib/api/types.ts`
  - Add `SlackAgentReviewResponse`.
- Modify `frontend/src/app/integrations/page.tsx`
  - Add Slack Agent execution button and result display.
- Modify `docs/portfolio-log.md`
  - Record API/UI milestone.

## Task 1: Backend API Test

- [ ] Write a failing test that:
  - syncs the mock Slack connector;
  - calls `/api/v1/integrations/slack/agent-review`;
  - asserts the response returns created review items;
  - asserts a stored ReviewItem payload has `agent_name="slack_agent"`,
    `prompt_version="slack-timeline:v1"`, and token/cost metadata.

- [ ] Run:

```powershell
uv run pytest backend/tests/test_slack_agent_api.py -v
```

Expected: fail because endpoint does not exist.

## Task 2: Backend Implementation

- [ ] Add `DeterministicSlackAgentModel`.
- [ ] Add `POST /api/v1/integrations/slack/agent-review`.
- [ ] Return:

```json
{
  "agent_name": "slack_agent",
  "status": "complete",
  "created_review_items": 1
}
```

- [ ] Run focused and full backend tests.

## Task 3: Frontend Integration

- [ ] Add frontend response type.
- [ ] Add "Slack Agent 실행" button to Slack integration card.
- [ ] Disable while running.
- [ ] Show result in the activity panel.
- [ ] Run `npm.cmd run build`.

## Task 4: Verification and Commit

- [ ] Backend tests pass.
- [ ] Frontend build passes.
- [ ] HTTP smoke for `/integrations` returns 200.
- [ ] Update portfolio log.
- [ ] Commit with `feat: expose slack agent review action`.

