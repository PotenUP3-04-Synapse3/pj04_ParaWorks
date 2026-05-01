# Slack Integration Preparation Runbook

This repository currently uses mock Slack data for the MVP harness. The real
Slack connector skeleton is ready for a future API client, but it does not make
network calls yet.

## Current Connector Boundary

Code:

- `backend/app/connectors/slack.py`

The connector maps Slack `conversations.history` message payloads into
ParaWorks `SourceEvent` records.

## Required Environment

```dotenv
SLACK_BOT_TOKEN=
SLACK_CHANNEL_IDS=C123,C456
SLACK_WORKSPACE_URL=https://your-workspace.slack.com
```

Keep these values unset in demo mode.

## Required Slack History Scopes

The connector records these required history scopes in `raw_metadata`:

- `channels:history`
- `groups:history`
- `im:history`
- `mpim:history`

These correspond to public channels, private channels, direct messages, and
multi-party direct messages.

## Next Implementation Step

Add a real Slack Web API client behind the `SlackApiClient` protocol:

```python
class RealSlackApiClient:
    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token

    def conversation_history(self, channel_id: str) -> list[dict]:
        ...
```

The client should call Slack `conversations.history`, handle cursor pagination,
and respect rate limits before handing payloads to `SlackConnector`.
