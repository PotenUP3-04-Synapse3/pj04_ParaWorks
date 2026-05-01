# Slack OAuth Installation Boundary Implementation Plan

**Goal:** Add a testable Slack OAuth installation boundary without storing raw
tokens in the database or accidentally using real Slack credentials during
portfolio/demo runs.

**Architecture:** Keep mock mode as the default. Generate signed OAuth install
state, exchange callback codes behind a Slack OAuth client, persist only
workspace metadata plus `token_ref` and a masked token, and leave production
secret storage as an explicit vault replacement point.

## Task 1: OAuth State And Client

Files:

- Create: `backend/app/connectors/slack_oauth.py`
- Create: `backend/tests/test_slack_oauth.py`

- [x] Write RED test for install URL signed state and secret hiding.
- [x] Write RED test for Slack `oauth.v2.access` code exchange with
  `httpx.MockTransport`.
- [x] Implement state signer, install URL builder, OAuth access payload, and
  OAuth client.

## Task 2: Token Storage Boundary

Files:

- Create: `backend/app/models/integrations.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/core/config.py`

- [x] Write RED test that callback completion stores no raw bot token in DB
  metadata.
- [x] Add `IntegrationConnection` with workspace metadata, scopes, `token_ref`,
  masked token, and status.
- [x] Add Slack OAuth settings.
- [x] Add local development token vault boundary.

## Task 3: API And Demo Safety

Files:

- Modify: `backend/app/api/v1/integrations.py`
- Modify: `backend/app/connectors/factory.py`
- Modify: `backend/tests/test_connector_factory.py`

- [x] Add install URL API.
- [x] Add OAuth callback API.
- [x] Add regression test that demo mode keeps mock sync active even when local
  Slack credentials exist.
- [x] Require `PARAWORKS_DEMO_MODE=false` before live Slack sync is selected.

## Task 4: Documentation And Verification

Files:

- Modify: `.env.example`
- Modify: `docs/superpowers/runbooks/slack-integration.md`
- Modify: `docs/portfolio-log.md`

- [x] Document Slack OAuth env settings and no-secret policy.
- [x] Document demo-mode cost guard.
- [x] Run focused OAuth tests.
- [x] Run focused factory/mock/review regression tests.
- [x] Run focused Ruff.
- [x] Run full backend pytest.
- [x] Run frontend build and Playwright visual smoke.
