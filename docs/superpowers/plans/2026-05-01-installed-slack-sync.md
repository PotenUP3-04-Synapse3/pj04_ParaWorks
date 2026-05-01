# Installed Slack Sync Token Boundary Implementation Plan

**Goal:** Let sync use an installed Slack OAuth connection when it is safe to do
so, while preserving demo-mode and no-secret guarantees.

**Architecture:** Add a sync-time connector factory that receives DB context and
a token vault. It selects installed Slack only when demo mode is disabled,
channel ids are configured, a connected workspace record exists, and the vault
can resolve the stored `token_ref`. Otherwise the existing mock/env fallback
behavior remains.

## Task 1: Factory Contract

Files:

- Modify: `backend/tests/test_connector_factory.py`
- Modify: `backend/app/connectors/factory.py`

- [x] Write RED test for installed connection token resolution.
- [x] Write test for missing-vault fallback to mock.
- [x] Add `get_sync_connector`.
- [x] Preserve `get_configured_connector` for legacy env-token live sync.

## Task 2: API Sync Wiring

Files:

- Modify: `backend/app/api/v1/integrations.py`
- Modify: `backend/tests/test_slack_oauth.py`

- [x] Update sync endpoint to use the sync-time factory with DB context.
- [x] Verify endpoint uses installed connection token via vault.
- [x] Verify sync API response does not expose raw token or `token_ref`.

## Task 3: Verification And Records

Files:

- Modify: `docs/superpowers/runbooks/slack-integration.md`
- Modify: `docs/portfolio-log.md`

- [x] Document installed sync selection and missing-vault fallback.
- [x] Run focused connector/OAuth/mock sync tests.
- [x] Run Python Ruff.
- [x] Run full backend pytest.
- [x] Run frontend build.
- [x] Run Playwright visual smoke on fresh alternate ports.
