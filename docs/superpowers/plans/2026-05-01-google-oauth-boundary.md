# Google OAuth Boundary Plan

## Goal

Add the same OAuth installation safety boundary for Gmail, Google Drive, and
Google Calendar that ParaWorks already has for Slack.

## Scope

- Generate signed Google OAuth install URLs for `gmail`, `drive`, and
  `calendar`.
- Validate callback state before exchanging temporary OAuth codes.
- Persist installed Google connections through `IntegrationConnection` with a
  `token_ref` and masked token only.
- Keep raw access and refresh tokens out of database metadata, API responses,
  logs, and frontend state.
- Show OAuth readiness on the integrations page without crowding the primary
  sync and agent action row.

## Cost And Security Notes

- This stage does not enable live Gmail, Drive, or Calendar sync yet.
- Demo mode remains mock-first, so portfolio smoke tests do not call Google APIs
  or trigger downstream LLM/embedding work.
- Future Google sync should fetch deltas first, then create review candidates,
  and only embed approved or changed chunks after hash/cursor checks.

## Verification

- RED: Google OAuth backend tests failed because `google_oauth.py` did not
  exist.
- RED: Playwright visual smoke failed because Google cards had no OAuth status
  blocks.
- GREEN: focused Google/Slack OAuth backend tests passed.
- GREEN: Playwright visual smoke passed with Google OAuth readiness assertions.
