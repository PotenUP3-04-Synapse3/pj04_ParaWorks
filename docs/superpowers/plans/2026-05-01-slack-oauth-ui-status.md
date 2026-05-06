# Slack OAuth UI Status Implementation Plan

**Goal:** Surface Slack OAuth readiness and connection status in the Integrations
page without exposing secrets or triggering live sync.

**Architecture:** Add a sanitized backend connection-status endpoint, consume it
from the existing Integrations page alongside manifests and install URL state,
and verify the UI with Playwright on desktop/mobile.

## Task 1: Sanitized Connection API

Files:

- Modify: `backend/app/api/v1/integrations.py`
- Modify: `backend/tests/test_slack_oauth.py`

- [x] Write RED test for `/api/v1/integrations/connections`.
- [x] Return connector type, workspace metadata, status, masked token, and
  scopes only.
- [x] Verify `token_ref` and raw vault values are not exposed.

## Task 2: Integrations UI

Files:

- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/integrations/page.tsx`

- [x] Fetch manifests, sanitized connections, and Slack install URL state.
- [x] Render Slack connection status with setup guidance.
- [x] Add install CTA that navigates only when OAuth is configured.
- [x] Keep mock/demo sync visible and usable when OAuth is not configured.

## Task 3: Verification And Records

Files:

- Modify: `frontend/e2e/visual-smoke.spec.ts`
- Modify: `docs/superpowers/runbooks/slack-integration.md`
- Modify: `docs/portfolio-log.md`

- [x] Write RED visual smoke test for Slack OAuth status.
- [x] Run focused backend test.
- [x] Run Python Ruff.
- [x] Run full backend pytest.
- [x] Run frontend production build.
- [x] Run Playwright visual smoke on fresh alternate ports.
- [x] Record portfolio and runbook notes.
