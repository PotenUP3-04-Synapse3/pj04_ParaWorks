# Google Installed Sync Boundary Plan

## Goal

Connect installed Gmail, Google Drive, and Google Calendar OAuth records to the
sync connector factory without enabling broad production-grade Google ingestion
yet.

## Scope

- Add a Google connector skeleton that maps Gmail messages, Drive files, and
  Calendar events into the existing `SourceEvent` contract.
- Resolve installed `IntegrationConnection.token_ref` values through the local
  token vault when `PARAWORKS_DEMO_MODE=false`.
- Keep demo mode mock-first even if Google connections exist locally.
- Fall back to mock mode when the local vault cannot resolve an installed token.
- Keep provider API calls mockable in tests and avoid real Google calls in CI.

## Cost And Security Notes

- This boundary creates the handoff from OAuth installation to sync, not the
  final delta/cursor engine.
- Future provider work should add Gmail `historyId`, Drive changes cursors, and
  Calendar sync tokens before enabling high-volume sync.
- Source fetch must happen before any LLM or embedding work, and unchanged
  sources should be skipped before review candidates are created.

## Verification

- RED: Google connector/factory tests failed because `backend.app.connectors.google`
  did not exist.
- GREEN: Google connector and factory tests passed after adding the skeleton.
- Full backend tests passed with 129 tests and 1 skipped pgvector integration
  test.
- Playwright visual smoke passed with 24 desktop/mobile route tests.
