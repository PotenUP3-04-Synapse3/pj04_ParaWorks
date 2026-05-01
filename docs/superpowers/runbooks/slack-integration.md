# Slack Integration Runbook

ParaWorks supports mock Slack data by default and has a live Slack Web API
client boundary for future OAuth-connected workspaces.

## Current Boundary

Code:

- `backend/app/connectors/slack.py`
- `backend/app/connectors/factory.py`
- `backend/app/ingestion/sync.py`

Responsibilities:

- `SlackWebApiClient` calls Slack `conversations.history` with bearer-token
  auth and cursor pagination.
- `SlackConnector` maps Slack message payloads into `SourceEvent`.
- `get_configured_connector` uses live Slack only when both token and channel
  ids are configured. Otherwise it falls back to mock mode.
- `sync_connector_events` handles `SyncJob`, duplicate skips, ingestion, and
  failure status.

## Required Environment

Keep these unset for demo and tests:

```dotenv
SLACK_BOT_TOKEN=
SLACK_CHANNEL_IDS=
SLACK_WORKSPACE_URL=https://your-workspace.slack.com
```

Use comma-separated channel ids:

```dotenv
SLACK_CHANNEL_IDS=C123,C456
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
- payload mapping preserves source id, permalink, timestamp, permission level,
  required scopes, and channel metadata.

## Cost And Security Notes

- Fetch source deltas before any LLM or embedding work.
- Preserve Slack timestamp and channel id as stable source identifiers.
- Keep raw private message text out of logs.
- The connector only creates source-backed review candidates; approved knowledge
  and RAG indexing still require the Review Queue boundary.
