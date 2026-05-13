# RAG Orchestrator Assistant Memory Design

Date: 2026-05-12

Owner: Developer C

## Goal

Upgrade the current `/search` surface from a one-shot company-memory query page
into a product-like AI assistant that stores conversations and messages per
logged-in user.

The assistant should feel like a business workflow surface, not an operations
dashboard. It should answer follow-up questions with conversation context,
preserve evidence and permission metadata, and keep token-cost observability in
`/agent-runs` instead of exposing cost details directly in the user-facing
conversation.

## Scope

In scope:

- database-backed assistant conversations and messages for each authenticated
  ParaWorks user;
- `/search` UI changes that make the page conversation-oriented;
- backend APIs used only by the assistant conversation surface;
- RAG answer persistence with citations, source snippets, hidden-match counts,
  and permission notices;
- token-saving conversation memory through summaries and a small recent-message
  window;
- explicit human approval before any future external action such as sync,
  embedding, or email sending.

Out of scope for this slice:

- changing `/agent-runs` UI beyond relying on it as the existing cost and
  observability page;
- changing Slack, Gmail, Google Drive, Calendar connector internals;
- changing document parsing, chunking, or pgvector indexing internals;
- sending real email;
- automatically syncing sources or running embeddings without user approval;
- editing unrelated pages.

## Product Principles

The `/search` assistant should optimize for trust and usefulness.

- Show answer evidence, source links, source snippets, permission level, and
  hidden-source notices.
- Do not show token cost, cache keys, or model pricing inside `/search`.
- Store cost and model metadata in `AgentRun` as the operational audit surface.
- Treat sync, embedding, email send, and other external actions as
  human-in-the-loop actions.
- Keep Korean business copy natural and concise.

## Ownership Boundary

Developer C owns:

- assistant conversation persistence;
- RAG orchestration for user questions;
- permission-aware answer packaging;
- HITL decision points for assistant actions;
- `/search` assistant UI.

Developer A continues to own Slack-specific ingestion and communication
intelligence.

Developer B continues to own Gmail, Google Drive, parsing, chunking, and
pgvector indexing internals.

Developer C may call stable APIs or shared contracts from A/B-owned systems, but
should not directly import or rewrite their agent internals.

## Data Model

Add an assistant-specific persistence model rather than reusing the existing
Messenger `messages` table. Messenger stores collaboration chat between people;
the assistant needs user-private AI conversation state, citations, permissions,
and RAG metadata.

Recommended tables:

### `assistant_conversations`

Fields:

- `id`: integer primary key;
- `user_id`: string, indexed;
- `title`: string;
- `summary`: text, nullable;
- `summary_updated_at`: datetime, nullable;
- `created_at`: datetime;
- `updated_at`: datetime.

The `summary` field stores compressed long-term conversation context. It is used
to reduce tokens and should not replace the full persisted message history.

### `assistant_messages`

Fields:

- `id`: integer primary key;
- `conversation_id`: foreign key to `assistant_conversations`;
- `role`: string enum-like value, `user` or `assistant`;
- `content`: text;
- `citations`: JSON list;
- `source_ids`: JSON list;
- `source_links`: JSON list;
- `source_snippets`: JSON list;
- `permission_level`: string, nullable;
- `hidden_match_count`: integer;
- `permission_notice`: string, nullable;
- `agent_run_id`: integer, nullable;
- `metadata`: JSON object;
- `created_at`: datetime.

Assistant messages should store enough evidence metadata to render a previous
answer without re-running RAG.

## API Design

Add assistant APIs under `/api/v1/assistant`.

Endpoints:

- `GET /api/v1/assistant/conversations`
  - Lists the current user's conversations ordered by `updated_at` descending.
- `POST /api/v1/assistant/conversations`
  - Creates a new conversation.
- `GET /api/v1/assistant/conversations/{conversation_id}/messages`
  - Returns messages only if the conversation belongs to the current user.
- `POST /api/v1/assistant/conversations/{conversation_id}/messages`
  - Stores the user message, runs permission-aware RAG, stores the assistant
    response, records the `AgentRun`, and returns both new messages.

Authorization:

- Every endpoint must use the current authenticated user.
- Users can only access their own assistant conversations.
- Admins should not automatically see another user's private assistant
  conversations through these endpoints.

## RAG Flow

The first implementation should keep the existing deterministic and pgvector
search paths.

Flow:

1. Load the conversation only for the current user.
2. Save the user's new message.
3. Build a compact query context from:
   - the conversation summary;
   - the latest few user/assistant turns;
   - the new user message.
4. Derive a RAG search question.
5. Call the existing RAG orchestrator service.
6. Store the assistant answer and evidence metadata.
7. Link the assistant message to the created `AgentRun` where available.
8. Update the conversation title and summary when needed.

The initial query-rewrite can be deterministic. A future paid model-based
rewriter must sit behind the model router, use fake clients in tests, and
preserve cost metadata.

## Conversation Memory and Cost Control

The assistant must not send all historical messages to an LLM or retriever.

Initial policy:

- include the current user message;
- include the latest six conversation messages at most;
- include the conversation summary when present;
- update the summary only after the conversation passes a configurable message
  count threshold;
- use deterministic summary updates in the first slice;
- keep paid summarization as a later explicit model-router feature.

This keeps follow-up questions useful without turning every request into an
expensive full-history prompt.

## `/search` UX

Only `/search` should change for this assistant slice.

Recommended layout:

- left column: conversation list and new conversation button;
- main column: message timeline and composer;
- evidence panel: citation/source details for the selected assistant response.

The message timeline should show:

- user messages;
- assistant answers;
- source count and hidden-source notice;
- source/evidence button;
- permission warning when relevant.

The message timeline should not show:

- token usage;
- estimated cost;
- cache key;
- model pricing.

Those details remain available through `/agent-runs`.

## HITL Extensions

The design should leave room for future assistant actions.

### Email Draft and Send

Future flow:

1. User asks the assistant to send an email.
2. Assistant detects an email intent.
3. Assistant drafts subject, recipients, and body in a business tone.
4. User reviews and edits the draft.
5. User explicitly approves send.
6. The orchestrator calls the mail connector action.
7. The result is audited.

The assistant must never send email directly from the first user prompt.

### Search Miss Recovery

Future flow:

1. User asks a question.
2. RAG finds too little evidence.
3. Assistant explains that the available knowledge is insufficient.
4. Assistant asks whether to sync selected sources and re-index changed data.
5. User explicitly approves.
6. Orchestrator calls existing sync and indexing boundaries.
7. Assistant re-runs retrieval and answers from the refreshed evidence.

This preserves cost control and prevents surprise external API calls.

## Error Handling

Expected errors:

- conversation not found or not owned by the current user;
- backend/RAG failure after the user message is stored;
- no visible evidence for the current user's permissions;
- source exists but is hidden by permission filters.

Behavior:

- return 404 for inaccessible conversations;
- store the user message even if the assistant response fails;
- return a recoverable error state to `/search`;
- avoid leaking hidden source content;
- report hidden-source counts only.

## Testing

Backend tests:

- conversation creation is scoped to the current user;
- users cannot read or write another user's conversation;
- posting a message stores both user and assistant messages;
- assistant messages preserve citations and hidden-match metadata;
- long conversations use summary/recent-window context instead of full history;
- cost/model data remains in `AgentRun` and is not required by `/search` UI.

Frontend tests or Playwright checks:

- `/search` loads conversation list;
- creating a new conversation works;
- asking a question appends user and assistant messages;
- evidence panel opens from an assistant response;
- token/cost/cache labels are absent from `/search`;
- mobile layout keeps the composer usable.

## Code Comment Policy

Implementation comments should be sparse and useful. Any new code comment added
for this slice must be written in Korean.

Examples of acceptable Korean comments:

- explaining why only a recent message window is used;
- explaining why hidden sources are counted but not exposed;
- explaining why external actions require explicit approval.

Avoid comments that simply restate obvious code.

## Rollout Plan

1. Add assistant conversation/message models and tests.
2. Add assistant schemas and service functions.
3. Add `/api/v1/assistant` routes.
4. Adapt the RAG service to expose the created `AgentRun` id if needed.
5. Update `/search` to use persisted conversations.
6. Verify backend tests, frontend build, and Playwright smoke.
7. Commit only the assistant-memory changes.

## Open Decisions

No blocking open decisions for the first slice.

Future implementation decisions:

- whether email draft approval should use Review Queue or a lighter action
  approval model;
- whether search miss recovery should offer source-level choices or a single
  "refresh available sources" action;
- when to replace deterministic summary/query rewrite with a structured model
  adapter.
