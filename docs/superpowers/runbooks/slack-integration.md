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

Responsibilities:

- `SlackWebApiClient` calls Slack `conversations.history` with bearer-token
  auth and cursor pagination.
- `SlackConnector` maps Slack message payloads into `SourceEvent`.
- `get_configured_connector` uses live Slack only when demo mode is disabled
  and both token and channel ids are configured. Otherwise it falls back to mock
  mode.
- `SlackOAuthStateSigner` signs install/callback state so callback payloads are
  not accepted blindly.
- `SlackOAuthClient` exchanges temporary OAuth codes with Slack
  `oauth.v2.access`.
- `IntegrationConnection` stores workspace metadata, scopes, token references,
  and masked tokens only. Raw tokens stay behind the token vault boundary.
- `sync_connector_events` handles `SyncJob`, duplicate skips, ingestion, and
  failure status.

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
- Slack API errors raise `SlackApiError`;
- OAuth install URLs contain signed state and never expose client secrets;
- OAuth code exchange is tested with fake Slack responses only;
- OAuth callback persistence stores token references and masked tokens, never
  raw bot tokens in database metadata;
- demo mode keeps mock sync active even if local Slack credentials exist;
- payload mapping preserves source id, permalink, timestamp, permission level,
  required scopes, and channel metadata.

## Cost And Security Notes

- Demo mode is the default so local tests do not accidentally call Slack or
  create ingestion churn from real workspace data.
- Fetch source deltas before any LLM or embedding work.
- Preserve Slack timestamp and channel id as stable source identifiers.
- Keep raw private message text out of logs.
- Store only `token_ref` plus a masked token in the database. The current local
  vault is an explicit development boundary; production should replace it with
  a managed secret store before enabling real customer workspaces.
- The connector only creates source-backed review candidates; approved knowledge
  and RAG indexing still require the Review Queue boundary.
