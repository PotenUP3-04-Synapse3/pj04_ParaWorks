# Google Integration Runbook

ParaWorks currently supports Gmail, Google Drive, and Google Calendar through a
mock connector, an OAuth installation boundary, and an installed-connection sync
skeleton.

## Current Boundary

Code:

- `backend/app/connectors/google_oauth.py`
- `backend/app/connectors/google.py`
- `backend/app/connectors/factory.py`
- `backend/app/api/v1/integrations.py`
- `backend/app/models/integrations.py`
- `frontend/src/app/integrations/page.tsx`

Responsibilities:

- `GoogleOAuthStateSigner` signs install/callback state per connector type.
- `build_google_oauth_install_url` creates install URLs for Gmail, Drive, and
  Calendar with read-only scopes.
- `GoogleOAuthClient` exchanges temporary OAuth codes and reads account identity
  with bearer-token userinfo calls.
- `complete_google_oauth_callback` persists installed connections with
  `token_ref`, masked token, account metadata, and scopes.
- `GoogleConnector` maps provider payloads into `SourceEvent` records for Gmail,
  Drive, and Calendar.
- `get_sync_connector` resolves installed Google `token_ref` values through the
  local token vault when demo mode is disabled.
- The Integrations UI shows Google OAuth readiness/status from sanitized API
  responses and keeps connect buttons outside primary sync/agent action rows.

## Required Environment

Keep demo mode enabled for portfolio demos and tests:

```dotenv
PARAWORKS_DEMO_MODE=true
```

OAuth install settings:

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/integrations/google/callback
GOOGLE_OAUTH_STATE_SECRET=replace-with-local-random-state-secret
```

Never commit `.env`, Google OAuth tokens, refresh tokens, exported mail content,
Drive documents, Calendar event payloads, or API responses containing private
workspace data.

## Required Scopes

Identity scopes for account display and connection matching:

- `openid`
- `email`

Read scopes by connector:

- Gmail: `https://www.googleapis.com/auth/gmail.readonly`
- Google Drive: `https://www.googleapis.com/auth/drive.readonly`
- Google Calendar: `https://www.googleapis.com/auth/calendar.readonly`

## Test Policy

Automated tests must never call Google APIs.

Use fake access payloads or `httpx.MockTransport` to verify:

- install URLs contain signed state and never expose client secrets;
- callback state rejects malformed signatures and connector mismatches;
- persisted connections store token references and masked tokens only;
- installed Google sync resolves tokens through the vault;
- demo mode keeps Google sync on mock connectors even if local OAuth connections
  exist;
- missing vault entries fall back to mock connectors instead of making partial
  external calls;
- `/api/v1/integrations/connections` never exposes token references;
- the Integrations page renders Google OAuth status without secrets.

## Cost And Security Notes

- OAuth installation is separate from live sync. Installing a connector should
  not immediately call LLMs or embedding models.
- The installed sync skeleton is intentionally mock-first in demo mode.
- Future live sync must add Gmail `historyId`, Drive changes cursors, and
  Calendar sync tokens before high-volume ingestion.
- Future live sync must fetch provider deltas first and skip unchanged sources
  before creating review candidates.
- Drive content should only be embedded after Review Queue approval or changed
  content hash checks.
- Raw access and refresh tokens stay behind the local token vault boundary.
  Production should replace the local vault with a managed secret store before
  enabling real customer workspaces.
