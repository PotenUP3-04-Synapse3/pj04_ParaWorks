# Slack Integration Runbook

ParaWorks supports mock Slack data by default and has a live Slack Web API
client boundary for future OAuth-connected workspaces.

## Current Boundary

Code:

- `backend/app/connectors/slack.py`
- `backend/app/connectors/factory.py`
- `backend/app/connectors/slack_oauth.py`
- `backend/app/models/integrations.py`
- `backend/app/ingestion/sync.py`
- `frontend/src/app/integrations/page.tsx`

Responsibilities:

- `SlackWebApiClient` calls Slack `conversations.history` with bearer-token
  auth, cursor pagination, and optional `oldest` timestamps for incremental
  history windows.
- `SlackConnector` maps Slack message payloads into `SourceEvent`.
- `get_sync_connector` uses an installed Slack connection first when demo mode
  is disabled, channel ids are configured, and the token vault can resolve the
  connection `token_ref`.
- `get_configured_connector` keeps the legacy environment-token path for local
  live sync experiments. Otherwise it falls back to mock mode.
- `SlackOAuthStateSigner` signs install/callback state so callback payloads are
  not accepted blindly.
- `SlackOAuthClient` exchanges temporary OAuth codes with Slack
  `oauth.v2.access`.
- `IntegrationConnection` stores workspace metadata, scopes, token references,
  and masked tokens only. Raw tokens stay behind the token vault boundary.
- The Integrations UI displays Slack connection readiness/status from sanitized
  API responses and never renders raw tokens or token references.
- `sync_connector_events` handles `SyncJob`, duplicate skips, ingestion,
  failure status, and Slack channel timestamp cursors derived from previously
  ingested source metadata.

## Required Environment

Keep demo mode enabled for portfolio demos and tests, even if local Slack
credentials are present:

```dotenv
PARAWORKS_DEMO_MODE=true
```

History sync token settings:

```dotenv
SLACK_BOT_TOKEN=
SLACK_CHANNEL_IDS=
SLACK_WORKSPACE_URL=https://your-workspace.slack.com
```

Use comma-separated channel ids:

```dotenv
SLACK_CHANNEL_IDS=C123,C456
```

OAuth install settings:

```dotenv
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_OAUTH_REDIRECT_URI=http://localhost:3000/integrations/slack/callback
SLACK_OAUTH_STATE_SECRET=replace-with-local-random-state-secret
```

Slack App configuration must include the exact same Redirect URL under
OAuth & Permissions. Slack treats these as different URLs:

- `http://localhost:3000/integrations/slack/callback`
- `http://127.0.0.1:3000/integrations/slack/callback`
- `http://localhost:8000/api/v1/...`

If Slack shows `redirect_uri did not match any configured URIs`, compare the
URL printed in the Slack error with `SLACK_OAUTH_REDIRECT_URI` and the Slack
App's Redirect URLs. Fix one side so they match exactly, then restart the
backend process so the install URL is rebuilt from the new environment value.

If live sync returns `Slack conversations.history failed: channel_not_found` or
`not_in_channel`, the bot token is valid enough to call Slack, but the app is
not able to read the configured channel. Check:

- `SLACK_CHANNEL_IDS` uses the exact channel id from the same workspace.
- The ParaWorks Slack App/Bot has been invited to the channel, especially for
  private channels and public channels that require bot membership.
- The installed app has the expected history/read scopes.

For local testing, prefer a low-risk channel such as `aibot-test`, invite the
ParaWorks bot there, then set `SLACK_CHANNEL_IDS` to that channel id before
turning `PARAWORKS_DEMO_MODE=false`.

The frontend callback route is
`/integrations/slack/callback`. It forwards Slack's `code` and signed `state`
to `/api/v1/integrations/slack/oauth/callback`, then renders only sanitized
workspace metadata. Do not expose raw tokens, OAuth secrets, or `token_ref`
values in callback UI, browser logs, docs, or screenshots.

In local MVP mode, the token vault is process memory. The database can keep a
Slack `IntegrationConnection` row after a backend restart, but the actual bot
token may no longer be resolvable from the local vault. The connections API
therefore returns sanitized `credential_status`:

- `available`: the current backend process can resolve the vault token and live
  sync can proceed if demo mode is disabled and channel ids are configured.
- `missing`: the connection metadata exists, but the local development vault no
  longer has the token. Re-run Slack OAuth or replace the local vault with a
  managed secret store before live sync.

Never commit `.env`, Slack tokens, OAuth tokens, or exported API responses that
contain private workspace content.

## Required Slack History Scopes

The connector records these required history scopes in `raw_metadata`:

- `channels:history`
- `groups:history`
- `im:history`
- `mpim:history`

These correspond to public channels, private channels, direct messages, and
multi-party direct messages.

## Test Policy

Automated tests must never call Slack.

Use `httpx.MockTransport` or fake `SlackApiClient` implementations to verify:

- bearer-token headers are attached;
- `conversations.history` receives the channel id and page limit;
- cursor pagination continues until `next_cursor` is empty;
- incremental Slack sync sends the latest stored channel timestamp as
  `oldest`;
- Slack API errors raise `SlackApiError`;
- OAuth install URLs contain signed state and never expose client secrets;
- OAuth code exchange is tested with fake Slack responses only;
- OAuth callback persistence stores token references and masked tokens, never
  raw bot tokens in database metadata;
- demo mode keeps mock sync active even if local Slack credentials exist;
- installed Slack sync resolves bot tokens from the vault and does not expose
  token refs or raw tokens in sync API responses;
- the Integrations page renders Slack OAuth status without secrets;
- payload mapping preserves source id, permalink, timestamp, permission level,
  required scopes, and channel metadata.

## Cost And Security Notes

- Demo mode is the default so local tests do not accidentally call Slack or
  create ingestion churn from real workspace data.
- Installed Slack sync requires a resolvable vault token and explicit channel
  ids. If the local vault is empty after a process restart, ParaWorks falls back
  to mock behavior instead of making partial or surprising external calls.
- Fetch source deltas before any LLM or embedding work.
- For Slack, source deltas use the latest stored `raw_metadata.channel_id` and
  `raw_metadata.ts` values as channel-level cursors, then Slack receives that
  timestamp as `oldest`.
- Preserve Slack timestamp and channel id as stable source identifiers.
- Keep raw private message text out of logs.
- Store only `token_ref` plus a masked token in the database. The current local
  vault is an explicit development boundary; production should replace it with
  a managed secret store before enabling real customer workspaces.
- The connector only creates source-backed review candidates; approved knowledge
  and RAG indexing still require the Review Queue boundary.
