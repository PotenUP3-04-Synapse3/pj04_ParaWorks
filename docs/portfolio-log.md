# ParaWorks Portfolio Log

Last updated: 2026-05-01

This document records ParaWorks work in a portfolio-friendly format. Keep adding
short entries here whenever the product, architecture, UX, verification, or
demo story changes.

## Portfolio Positioning

ParaWorks is a Korean-first, multi-agentic Slack-style collaboration and
knowledge review workspace for business users. The MVP demonstrates how work
messages, SaaS connector events, and review workflows can become searchable,
permission-aware organizational knowledge.

## Current Narrative

The project started as an Adapter-First Demo Harness and evolved into a more
product-shaped MVP:

- A Korean-first business UX with English switching for international-ready use.
- A Slack-like Messenger surface for team conversation and collaboration.
- A review queue that turns selected messages and connector evidence into
  human-confirmed knowledge candidates.
- A Docker-free SQLite smoke mode so the product can be run and demonstrated
  quickly even when Postgres, Redis, and MinIO are unavailable.
- A Slack connector boundary prepared for future real Slack Web API ingestion.

## Work Completed

### Korean-First UX and Messenger MVP

- Added Korean default shell copy and a Korean/English language switch.
- Added `/messages` as a Slack-like messenger screen with channels, timeline,
  and message composer.
- Added backend message APIs for listing channels, listing messages, and
  posting messages.
- Fixed SSE completion behavior so successful sync completion is not shown as
  a stream error.

Portfolio angle:

- Shows product localization for the first target market: Korean business users.
- Demonstrates moving beyond a technical harness into a familiar collaboration
  experience.

### SQLite Smoke Mode

- Added `scripts/start-smoke.ps1` for Docker-free local demos.
- Added a smoke runbook and updated local development and verification docs.
- Smoke mode starts FastAPI and Next.js against a temporary SQLite database.

Portfolio angle:

- Shows practical engineering for demo reliability and onboarding speed.
- Reduces environment friction, which matters for stakeholder demos and hiring
  portfolio walkthroughs.

### Messenger Persistence

- Added SQLAlchemy models for `message_channels` and `messages`.
- Changed message service behavior from process memory to database-backed
  persistence.
- Seeded demo channels and messages on first use against an empty database.

Portfolio angle:

- Shows the transition from UI prototype to stateful MVP infrastructure.
- Establishes a foundation for analytics, search, review, and audit history.

### Messenger to Review Queue

- Added `POST /api/v1/messages/messages/{message_id}/send-to-review`.
- Added UI action to send a message into the review workflow.
- Created review items with message snippets and `paraworks://messages/...`
  source links.

Portfolio angle:

- Connects the Slack-like messenger directly to ParaWorks' knowledge workflow.
- Shows a concrete "conversation to organizational knowledge" product loop.

### Slack Connector Preparation

- Added `backend/app/connectors/slack.py` with a testable `SlackApiClient`
  protocol boundary.
- Added tests for Slack message payload mapping into ParaWorks `SourceEvent`
  records.
- Added Slack integration runbook and environment placeholders:
  `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_IDS`, `SLACK_WORKSPACE_URL`.

Portfolio angle:

- Shows adapter-first architecture: real SaaS APIs can be connected without
  coupling product logic to vendor SDK details.
- Sets up future real Slack ingestion with pagination, rate limits, OAuth, and
  permission mapping.

## Verification Evidence

Latest known verified state:

- Backend tests: `uv run pytest backend/tests -v` -> 27 passed.
- Frontend build: `npm.cmd run build` -> passed.
- Smoke runtime:
  - `http://127.0.0.1:3000/messages`
  - `http://127.0.0.1:3000/dashboard`
  - `http://127.0.0.1:3000/review`
- Browser smoke covered message posting, language switching, sending a message
  to review, and confirming the created review item on `/review`.

## Portfolio Demo Script

1. Start the SQLite smoke environment with `.\scripts\start-smoke.ps1`.
2. Open `/dashboard` to show the product overview.
3. Open `/messages` to show Korean-first Slack-like collaboration.
4. Post or select a message and send it to the review queue.
5. Open `/review` to show the message as a knowledge review candidate.
6. Explain that connector data and messenger data share the same review/search
   architecture.
7. Point to the Slack connector boundary as the next real-world integration
   step.

## Next Portfolio-Worthy Milestones

- Implement `RealSlackApiClient` with Slack Web API cursor pagination and
  rate-limit handling.
- Add Slack OAuth install flow and token storage decisions.
- Map Slack channel/private-message permissions into ParaWorks review/search
  access rules.
- Add message-to-knowledge actions such as "create decision record" and
  "create todo".
- Add focused frontend regression tests for Messenger and review actions.

## Product North Star Update: Multi-Agent Knowledge Automation

Recorded on 2026-05-01.

ParaWorks' final target is an AI-agentic company memory platform. The agent
system will use multi-agent orchestration with LangChain 1.x and LangGraph 1.x
to automate:

- Email summarization, review, timeline creation, and history creation.
- Slack channel/message summarization, review, timeline creation, and history
  creation.
- RAG over generated timelines/history and internal company documents.
- Permission-aware answers for Korean business users.

The first recommended vertical slice is:

Slack channel/messages -> agentic summary and review -> timeline/history
candidates -> Review Queue.

Portfolio angle:

- Shows the transition from MVP collaboration surface to AI orchestration
  platform.
- Makes token cost optimization a product and architecture requirement from the
  start, not a late performance cleanup.
- Supports a three-developer split across agent runtime, data/RAG, and product
  UX.

## Collaboration Guide Update: Equal Agent Ownership

Recorded on 2026-05-01.

Added `AGENTS.md` as the repo-level collaboration guide for human developers
and coding assistants. The guide changes the team split from technical layers
to equal agent ownership:

- Slack Agent.
- Mail and Document Agent.
- RAG and Orchestrator Agent.

It also codifies evidence-first AI output, Review Queue as the trust boundary,
permission propagation, token-cost accounting, fake-LLM testing, and assistant
behavior rules for Codex, Claude Code, Gemini, and similar tools.

Portfolio angle:

- Shows that ParaWorks is being developed as a serious multi-agent system with
  team-scale engineering discipline.
- Makes AI safety, cost optimization, permissions, and human review explicit
  development compliance requirements.

## Integration Pipeline Update: Assistant-Safe Merging

Recorded on 2026-05-01.

Updated `AGENTS.md` with a development pipeline for three independent agent
tracks and coding assistants:

- shared contract branch first;
- feature branch per agent;
- integration branch for frequent green merges;
- contract tests as the merge gate;
- human decision points for schema, permission, cost, trust-boundary, and
  duplicate-resolution policy changes.

Portfolio angle:

- Demonstrates that ParaWorks is designed for AI-assisted team development, not
  only AI-powered product features.
- Shows awareness that Codex can help resolve conflicts, but stable contracts,
  registry-based integration, and verification gates must exist before the
  merge.

## UX Direction Update: Slack-Like Workspace

Recorded on 2026-05-01.

Started a frontend UX pass to make ParaWorks feel like a Korean-first
Slack-like business workspace rather than a plain demo harness.

Planned scope:

- darker workspace navigation rail;
- top command/search entry for future AI/RAG usage;
- richer Messages channel surface;
- Tools/Apps-style Integrations page;
- cleaner Korean-first operational copy.

Implemented scope:

- redesigned the shared app shell into a Slack-like workspace rail;
- added a top command/search bar and agent readiness affordance;
- upgraded Messages with denser channel navigation, timeline styling, review
  actions, and an anchored composer;
- upgraded Integrations into a Tools/Apps surface with connector readiness and
  sync activity panel.

Verification evidence:

- `npm.cmd run build` from `frontend` passed without warnings.
- HTTP smoke returned 200 for `/integrations`, `/messages`, and `/dashboard`
  on `http://127.0.0.1:3000`.

Portfolio angle:

- Shows product sense and UX architecture, not only backend AI engineering.
- Prepares the interface for Slack Agent, Review Inbox, and RAG Orchestrator
  experiences without a later full layout rewrite.

## Agent Development Update: Slack Agent Skeleton

Recorded on 2026-05-01.

Started the first functional agent track after the shared runtime and registry
contracts. The Slack Agent skeleton is scoped to:

- accept shared `EvidencePacket` input;
- use a fake/model client boundary instead of live LLM calls;
- return `AgentRunResult`;
- preserve source links, snippets, and strictest permission level;
- record token/cost metadata.

Portfolio angle:

- Shows the project moving from architecture contracts into actual agent
  implementation.
- Keeps the work merge-friendly because Slack Agent lives in its own owned
  package and integrates only through shared runtime contracts.

## Agent Development Update: Slack Agent Review Bridge

Recorded on 2026-05-01.

Started the bridge that turns persisted Slack source chunks into shared
`EvidencePacket` input, runs the Slack Agent, and persists agent output as
`ReviewItem(status="pending_review")`.

Portfolio angle:

- Shows the first real product loop for agentic Slack knowledge extraction:
  source evidence -> agent runtime -> human review.
- Preserves the project compliance story by carrying source links, snippets,
  permission level, prompt version, cache key, and token/cost metadata into the
  Review Queue.

## Agent Development Update: Slack Agent API and UI

Recorded on 2026-05-01.

Next milestone is exposing the Slack Agent Review bridge through the product:

- backend endpoint for Slack Agent Review generation;
- deterministic demo model instead of live LLM calls;
- frontend Tools action to run the Slack Agent after mock Slack sync;
- activity panel result showing how many Review Queue items were created.

Portfolio angle:

- Turns agent architecture into a user-visible workflow.
- Demonstrates cost-safe AI development by using a deterministic local model
  boundary before enabling paid LLM provider calls.

## UX Update: Agent-Aware Review Inbox

Recorded on 2026-05-01.

Next UI milestone is upgrading `/review` from a generic review list into an
agent-aware activity inbox:

- AI Agent-generated candidates are visibly labeled.
- Prompt version, token usage, estimated cost, cache key, permission, and
  confidence become inspectable from the Review UI.
- Source Evidence Drawer gets clean Korean copy and clearer evidence links.

Portfolio angle:

- Makes the human-review trust boundary visible to users and interviewers.
- Connects the token-cost optimization requirement to a concrete product
  surface instead of keeping it hidden in backend metadata.

Implemented scope:

- Reworked `/review` into an Activity Inbox-style review queue.
- Replaced corrupted Korean UI copy.
- Added AI Agent badges for agent-generated Review Items.
- Exposed prompt version, token count, estimated cost, cache key, confidence,
  permission, and source evidence in the UI.
- Cleaned up the Source Evidence Drawer copy and layout.

Verification evidence:

- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted after build to clear stale Next.js cache.
- HTTP smoke returned 200 for `/review`, `/integrations`, and `/health`.

## Agent Runtime Update: AgentRun Cost Audit Model

Recorded on 2026-05-01.

Next backend milestone is persisting every agent execution as an `AgentRun` row
so token usage, estimated cost, prompt version, cache key, permission level, and
run status can be audited beyond the ReviewItem payload.

Portfolio angle:

- Shows that token-cost optimization is backed by durable observability, not
  only UI labels.
- Creates the shared audit foundation needed by Slack Agent, Mail/Document
  Agent, and RAG/Orchestrator Agent.

Implemented scope:

- Added the `agent_runs` table and `AgentRun` model.
- Persisted one `AgentRun` row for each Slack Agent Review execution.
- Linked generated Review Items back to the originating agent run through
  `payload.agent_run_id`.
- Stored prompt version, cache key, model name, token usage, estimated cost,
  source window, permission level, and run metadata.

Verification evidence:

- `uv run pytest backend/tests/test_agent_run_model.py backend/tests/test_db_init.py -v`
  passed.
- `uv run pytest backend/tests -v` passed with 40 backend tests.

## Agent Development Update: Mail/Document Agent Slice

Recorded on 2026-05-01.

Next agent-track milestone is giving Developer B an independently owned agent
slice for Gmail and Drive evidence while preserving the same shared runtime
contract used by Slack Agent.

Portfolio angle:

- Demonstrates that ParaWorks is not a single hard-coded Slack demo; it now has
  a repeatable multi-agent backend pattern across communication and document
  sources.
- Shows practical 3-person division of labor: Slack Agent, Mail/Document Agent,
  and RAG/Orchestrator Agent can evolve with the same `EvidencePacket`,
  `AgentRunResult`, `AgentRun`, and Review Queue boundaries.

Implemented scope:

- Added `mail_document_agent` with manifest, model protocol, deterministic
  local model, and `MailDocumentAgent`.
- Added a bridge that builds evidence packets from Gmail and Drive chunks,
  excludes Slack chunks, persists `AgentRun`, and links Review Items through
  `payload.agent_run_id`.
- Added `POST /api/v1/integrations/mail-docs/agent-review` for deterministic
  MVP smoke testing without paid LLM calls.

Verification evidence:

- `uv run pytest backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py -v`
  passed.
- `uv run pytest backend/tests -v` passed with 44 backend tests.

## UX Update: Integrations Multi-Agent Actions

Recorded on 2026-05-01.

Next product milestone is making the second backend agent visible from the
same Integrations surface users already use for mock connector smoke testing.

Portfolio angle:

- Shows that the product can expose multiple independently owned agents without
  duplicating UI state or endpoint-specific response types.
- Makes the 3-person agent split tangible in the app: Slack Agent and
  Mail/Docs Agent can both be run from the Korean business-user workflow.

Implemented scope:

- Generalized the frontend agent-review response type to `AgentReviewResponse`.
- Replaced Slack-only action state with reusable agent action descriptors.
- Added Mail/Docs Agent buttons to Gmail and Drive cards.
- Kept Korean UX copy intact and displayed completed agent names in friendly
  labels.

Verification evidence:

- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-mail-docs-ui.db`.
- HTTP smoke returned 200 for `/health`, `/integrations`, and `/dashboard`.
- Gmail sync, Drive sync, and `POST /api/v1/integrations/mail-docs/agent-review`
  returned `agentName=mail_document_agent` and `created=1`.

## Agent Development Update: RAG Orchestrator Agent

Recorded on 2026-05-01.

Next core-product milestone is giving users a question-answering endpoint over
the company memory evidence that Slack, Gmail, Drive, and review workflows have
already collected.

Portfolio angle:

- Completes the three-track agent split: Slack Agent, Mail/Document Agent, and
  RAG/Orchestrator Agent now each have an independently testable backend slice.
- Shows a cost-safe RAG migration path: deterministic keyword retrieval now,
  vector DB and LangGraph orchestration later without changing the public answer
  contract.
- Demonstrates permission-aware RAG behavior by hiding restricted sources for
  viewer users while reporting hidden matches.

Implemented scope:

- Added `rag_orchestrator_agent` with manifest, deterministic model, answer
  dataclasses, and cost metadata.
- Added permission-aware retrieval over existing `DocumentChunk` evidence.
- Added `POST /api/v1/ask` returning answer text, source links, snippets,
  permission notices, cache key, model name, token usage, and estimated cost.

Verification evidence:

- `uv run pytest backend/tests/test_rag_orchestrator_agent.py backend/tests/test_rag_orchestrator_service.py backend/tests/test_ask_api.py -v`
  passed.
- `uv run pytest backend/tests -v` passed with 50 backend tests.

## Commit Timeline

- `091c21f feat: add Korean UX and messenger MVP`
- `82e76d1 chore: add SQLite smoke mode`
- `b68caaa feat: persist messenger data`
- `53be213 feat: send messenger items to review`
- `e90d4f9 feat: prepare Slack connector boundary`
- `ce5c23e docs: define agentic Slack timeline slice`
- `1667aba feat: add agent runtime contracts`
- `8fe0190 feat: add agent registry contract`
- `e15ad16 feat: refresh workspace UI`
- `65b36ac feat: add slack agent skeleton`
- `39f96c9 feat: connect slack agent to review queue`
- `7b0a6f5 feat: expose slack agent review action`
- `924f9d8 feat: improve agent-aware review UI`
- `e7c6927 feat: persist agent run metadata`
- `e53bec0 feat: add mail document agent slice`
- `79e7bc7 feat: expose mail docs agent in integrations`
