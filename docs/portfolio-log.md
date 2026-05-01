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

## UX Update: Company Memory Ask Workbench

Recorded on 2026-05-01.

Next product milestone is making the RAG Orchestrator visible to Korean
business users through the existing Search surface.

Portfolio angle:

- Turns the backend `/api/v1/ask` contract into an inspectable product workflow:
  question, AI answer, citations, raw matching evidence, permission notice, and
  cost metadata are visible together.
- Shows that ParaWorks treats RAG answers as auditable outputs, not opaque chat
  bubbles.
- Keeps the demo cost-safe by using the deterministic orchestrator while still
  exposing token and estimated-cost fields.

Implemented scope:

- Added frontend `AskResponse` type.
- Reworked `/search` into a Company Memory workbench.
- One query now calls both `/api/v1/ask` and `/api/v1/search` using viewer
  permissions.
- Rendered answer text, source links, token count, estimated cost, hidden
  match count, permission notice, cache key, model name, and raw evidence.

Verification evidence:

- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-ask-ui.db`.
- HTTP smoke returned 200 for `/health`, `/search`, and `/dashboard`.
- Gmail sync, Drive sync, and `POST /api/v1/ask` returned
  `agentName=rag_orchestrator_agent`, `sources=2`, `hidden=0`, and `tokens=100`.

## Observability Update: Agent Run Cost Dashboard

Recorded on 2026-05-01.

Next operations milestone is making AI execution cost and token usage visible
from the product, not only stored in the database.

Portfolio angle:

- Shows AI cost governance as a first-class product feature.
- Gives the three-agent split a shared observability surface: Slack Agent,
  Mail/Docs Agent, and future RAG runs can be compared through one audit table.
- Demonstrates a production-minded pattern where every agent run has prompt,
  model, token, cost, permission, and cache metadata.

Implemented scope:

- Added read-only `GET /api/v1/agent-runs`.
- Returned aggregate run count, total tokens, estimated total cost, and recent
  run details.
- Added frontend `AgentRunsResponse` and `AgentRunSummaryItem` types.
- Reworked `/dashboard` with Agent execution count, estimated cost, token total,
  and recent Agent Runs panel.

Verification evidence:

- `uv run pytest backend/tests/test_agent_runs_api.py -v` passed.
- `uv run pytest backend/tests -v` passed with 51 backend tests.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-agent-runs.db`.
- Slack Agent and Mail/Docs Agent smoke run produced `totalRuns=2`,
  `totalTokens=226`, and `estimatedCost=0.000063`.
- HTTP smoke returned 200 for `/health`, `/dashboard`, and `/search`.

## Observability Update: RAG AgentRun Persistence

Recorded on 2026-05-01.

Next observability milestone is ensuring the RAG Orchestrator participates in
the same AgentRun audit trail as Slack Agent and Mail/Docs Agent.

Portfolio angle:

- Completes the shared three-agent audit story: Slack extraction, Mail/Docs
  extraction, and RAG question answering all create durable cost records.
- Shows that every user-facing AI answer can be traced to prompt version, model,
  token usage, estimated cost, cache key, permission level, and source count.
- Strengthens the token-cost optimization requirement by making RAG asks visible
  in the same dashboard totals.

Implemented scope:

- Persisted one `AgentRun` for each `answer_question_with_rag` execution.
- Stored question text, source count, hidden match count, source type, and cache
  hit metadata.
- Kept the public `/api/v1/ask` response shape unchanged while allowing
  `/api/v1/agent-runs` and `/dashboard` to include RAG ask runs.

Verification evidence:

- `uv run pytest backend/tests/test_rag_orchestrator_service.py -v` passed.
- `uv run pytest backend/tests -v` passed with 52 backend tests.
- Smoke server restarted with `.tmp/paraworks-rag-agent-run.db`.
- Gmail sync, Drive sync, and `POST /api/v1/ask` produced
  `askAgent=rag_orchestrator_agent`, `askTokens=100`, `totalRuns=1`,
  `totalTokens=100`, and `latestQuestion=Redis job state`.
- HTTP smoke returned 200 for `/health`, `/dashboard`, and `/search`.

## Knowledge Update: Review Approval Promotion

Recorded on 2026-05-01.

Next product milestone is closing the human-review loop so approved agent
candidates become durable company memory records.

Portfolio angle:

- Completes the source evidence -> agent candidate -> human approval -> company
  memory loop.
- Shows that ParaWorks keeps human approval as the trust boundary before
  writing durable history, decision, and task records.
- Preserves the audit story by carrying source links, source snippets,
  confidence, permission level, and approved review status into knowledge
  tables.

Implemented scope:

- Added `promote_review_item` in `backend/app/knowledge/promotion.py`.
- Mapped `decision_record` Review Items into `DecisionRecord`.
- Mapped `history_event` Review Items into `HistoryEvent`.
- Mapped `todo` Review Items into `Todo`.
- Called promotion from the existing Review approve endpoint.

Verification evidence:

- `uv run pytest backend/tests/test_review_knowledge_promotion.py -v` passed.
- `uv run pytest backend/tests -v` passed with 55 backend tests.
- Smoke server restarted with `.tmp/paraworks-review-promotion.db`.
- Slack sync produced 3 pending Review Items, approving one returned
  `approvedStatus=approved` and `approvedType=todo`.
- HTTP smoke returned 200 for `/health`, `/review`, and `/dashboard`.

## Product Update: Knowledge Library

Recorded on 2026-05-01.

Next user-facing milestone is making approved company memory visible after
Review Queue approval.

Portfolio angle:

- Turns durable knowledge rows into an inspectable product surface.
- Shows the completed workflow from Slack evidence to Review approval to
  approved decisions, history, and todos.
- Provides a natural next step toward vectorizing approved company memory for
  production RAG.

Implemented scope:

- Added read-only `GET /api/v1/knowledge`.
- Returned approved decisions, history events, todos, counts, source evidence,
  confidence, permission, and review status.
- Added frontend `KnowledgeResponse` and `KnowledgeItem` types.
- Added `/knowledge` page with summary cards and evidence-preserving records.
- Added Knowledge navigation labels in Korean and English.

Verification evidence:

- `uv run pytest backend/tests/test_knowledge_api.py -v` passed.
- `uv run pytest backend/tests -v` passed with 56 backend tests.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-knowledge-library.db`.
- Slack sync and approving all 3 Review Items produced `decisions=1`,
  `history=1`, and `todos=1` from `/api/v1/knowledge`.
- HTTP smoke returned 200 for `/health`, `/knowledge`, `/review`, and
  `/dashboard`.

## RAG Update: Approved Knowledge Retrieval

Recorded on 2026-05-01.

Next retrieval milestone is allowing the RAG Orchestrator to answer from
human-approved company memory, not only raw source chunks.

Portfolio angle:

- Connects Knowledge Library records back into the user-facing Ask workflow.
- Shows the intended learning loop: raw evidence is reviewed, promoted into
  company memory, then reused as trusted RAG context.
- Keeps the permission story intact by applying hidden-match behavior to
  approved knowledge records as well as raw document chunks.

Implemented scope:

- Added `RagEvidenceCandidate` as a common retrieval candidate for raw chunks
  and approved knowledge.
- Added approved `DecisionRecord`, `HistoryEvent`, and `Todo` retrieval to the
  RAG Orchestrator service.
- Preserved source links and source snippets from approved knowledge records in
  `EvidencePacket`.
- Kept `/api/v1/ask` response shape unchanged.

Verification evidence:

- `uv run pytest backend/tests/test_rag_orchestrator_service.py backend/tests/test_ask_api.py -v`
  passed.
- `uv run pytest backend/tests -v` passed with 59 backend tests.
- Smoke server restarted with `.tmp/paraworks-knowledge-rag.db`.
- Slack sync and approving all 3 Review Items followed by `POST /api/v1/ask`
  for `Redis queues` returned `askAgent=rag_orchestrator_agent`,
  `sourceCount=2`, and `hidden=0`.
- HTTP smoke returned 200 for `/health`, `/search`, `/knowledge`, and
  `/dashboard`.

## Observability Update: AgentRun Detail View

Recorded on 2026-05-01.

Next observability milestone is inspecting one AI execution from dashboard
summary to prompt, model, token, cost, cache, permission, and metadata detail.

Portfolio angle:

- Makes AI orchestration cost and behavior auditable at the individual run
  level.
- Gives reviewers a concrete UI for explaining prompt versions, token usage,
  cache keys, permission level, and runtime metadata.
- Connects the executive dashboard to an engineer-facing trace view without
  changing the agent execution contract.

Implemented scope:

- Added `GET /api/v1/agent-runs/{id}` with a shared AgentRun serializer.
- Added `token_usage` to AgentRun API payloads while preserving flat token
  fields for existing UI code.
- Added `/agent-runs/[id]` frontend detail page.
- Linked recent dashboard AgentRun rows to their detail pages.

Verification evidence:

- `uv run pytest backend/tests/test_agent_runs_api.py -v` passed.
- `uv run pytest backend/tests -v` passed with 61 backend tests.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-agent-run-detail.db`.
- Gmail and Drive sync followed by `POST /api/v1/ask` produced AgentRun `8`
  with `agent=rag_orchestrator_agent`, `tokens=136`, and
  `question=Redis job state` from `/api/v1/agent-runs/8`.
- HTTP smoke returned 200 for `/health`, `/dashboard`, `/agent-runs/8`, and
  `/review`.
- Browser smoke opened `/agent-runs/8`, rendered the Rag Orchestrator run
  details, and reported no console errors.

## Harness Reliability: Isolated Frontend Smoke Cache

Recorded on 2026-05-01.

During browser retesting, the AgentRun detail page rendered without Tailwind
styles because the running Next dev server and `npm run build` shared the same
`.next` directory.

Portfolio angle:

- Shows debugging across browser rendering, CSS asset serving, Next build
  artifacts, and local smoke scripts.
- Turns a flaky local-demo failure into a repeatable regression test.
- Protects future AI-assisted workflows where test/build commands may run
  while the smoke UI remains open.

Implemented scope:

- Added `NEXT_DIST_DIR` support to `frontend/next.config.ts`.
- Updated `scripts/start-smoke.ps1` so smoke dev uses `.next-smoke` instead of
  the production build `.next` directory.
- Added `backend/tests/test_smoke_frontend_cache.py` to guard the cache
  isolation contract.

Verification evidence:

- Reproduced the broken page as a CSS 404 for
  `/_next/static/css/app/layout.css`.
- `uv run pytest backend/tests/test_smoke_frontend_cache.py -v` failed before
  the fix and passed after the fix.
- Restarted smoke with `.tmp/paraworks-agent-run-detail.db`.
- Confirmed `/agent-runs/8` and its CSS file returned 200 before and after
  `npm.cmd run build` while the smoke dev server stayed open.
- Browser smoke reloaded `/agent-runs/8` and rendered the styled AgentRun cards.

## Observability Update: AgentRun Operations Summary

Recorded on 2026-05-01.

Next operations milestone is moving from single-run inspection to an overview
that compares cost, token usage, cache behavior, and status across all agent
tracks.

Portfolio angle:

- Shows AI cost governance at both detail and aggregate levels.
- Gives the three-developer agent split a shared operational dashboard:
  Slack Agent, Mail/Docs Agent, and RAG Orchestrator can be compared without
  coupling their internals.
- Turns token-cost optimization into a visible product workflow instead of a
  hidden backend concern.

Implemented scope:

- Added `GET /api/v1/agent-runs/summary`.
- Returned total runs, token totals, estimated cost, average cost, average
  tokens per run, cache hits, cache hit rate, status counts, and per-agent
  cost/token breakdowns.
- Added frontend `AgentRunSummaryResponse` and `AgentRunAgentSummary` types.
- Added `/agent-runs` as an operations summary page with cards, per-agent
  table, status distribution, and links to run detail pages.
- Added `AI 실행` / `AI Runs` navigation labels and linked the dashboard
  AgentRun panel to the full operations page.

Verification evidence:

- `uv run pytest backend/tests/test_agent_runs_api.py -v` passed.
- `npm.cmd run build` from `frontend` passed and included `/agent-runs`.
- Smoke server restarted with `.tmp/paraworks-agent-run-detail.db`.
- HTTP smoke returned 200 for `/health`, `/agent-runs`, `/dashboard`, and
  `/api/v1/agent-runs/summary`.
- Summary smoke returned `totalRuns=8`, `totalTokens=666`,
  `cacheHitRate=0.0`, and `agents=2`.
- Browser smoke opened `/agent-runs` and confirmed the `AI 실행 관측`,
  `Agent별 비용과 토큰`, `상태 분포`, and `최근 실행 로그` sections.

## Agent Platform Update: Review, Vector, and Orchestration Foundations

Recorded on 2026-05-01.

Next platform milestone is preparing the product loop for real multi-agent
implementation: stricter human review, vector-ready retrieval, and a
LangGraph-ready workflow contract.

Portfolio angle:

- Shows the core AI safety boundary: generated candidates cannot be approved
  into company memory until required fields and evidence are present.
- Introduces a vector-store abstraction without forcing paid embeddings or a
  production Vector DB during MVP development.
- Makes the future LangGraph migration concrete by fixing state and node names
  before adding the dependency.

Implemented scope:

- Added Review promotion preview and approval validation for decision,
  history, and todo review item types.
- Added frontend Review Queue preview cards showing the exact normalized record
  shape that will be promoted on approval.
- Added a permission-aware `InMemoryVectorStore` with hidden-match counting and
  exportable document shape for future pgvector, Chroma, or Qdrant adapters.
- Added a RAG candidate to `VectorDocument` projection bridge.
- Added a local company-memory workflow skeleton with append-only audit state
  and LangGraph-ready node order: collect evidence, draft review candidates,
  retrieve company memory, answer with RAG.

Verification evidence:

- Review preview and promotion tests passed.
- Vector store and existing RAG service tests passed.
- Agent orchestration skeleton tests passed.
- Frontend build passed after Review Queue preview UI changes.
- Full backend suite passed with 70 tests.
- Smoke server restarted with `.tmp/paraworks-review-vector-langgraph.db`.
- Slack sync created 3 pending review items; promotion preview returned
  `canApprove=true` and `target=todo`.
- HTTP smoke returned 200 for `/health`, `/review`, `/search`, and
  `/agent-runs`.
- Browser smoke opened `/review` and confirmed approval preview cards for
  todo, history, and decision records.

## RAG Infrastructure Update: PostgreSQL + pgvector Adapter

Recorded on 2026-05-01.

Confirmed PostgreSQL + pgvector as the production RAG storage direction while
preserving SQLite smoke mode for fast demos.

Portfolio angle:

- Shows a practical RAG infrastructure choice instead of leaving vector storage
  vague.
- Keeps company memory, permissions, source evidence, and vector search close
  to the same transactional Postgres boundary.
- Avoids extra operational complexity from a separate vector database during
  MVP development.

Implemented scope:

- Added `PgVectorStore` with schema SQL, upsert SQL, permission-filtered search
  SQL, and hidden-match accounting.
- Added `PgVectorConfig` with table-name and embedding-dimension validation.
- Added Docker init SQL for `rag_vector_documents`, `embedding vector(1536)`,
  ivfflat cosine index, and permission index.
- Documented PostgreSQL + pgvector as the default RAG storage path in
  `AGENTS.md` and `README.md`.

Verification evidence:

- `uv run pytest backend/tests/test_pgvector_store.py -v` passed.
- `uv run pytest backend/tests -v` passed with 74 backend tests.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-pgvector-adapter.db`.
- HTTP smoke returned 200 for `/health`, `/dashboard`, `/review`, `/search`,
  and `/agent-runs`.
- Browser smoke opened `/search` and confirmed the Company Memory/Search
  surface still rendered under SQLite smoke mode.

## RAG Infrastructure Update: Vector Indexing Pipeline

Recorded on 2026-05-01.

Added the first indexing pipeline that turns current company memory into
embeddable vector documents while keeping local MVP smoke mode independent from
live Postgres.

Portfolio angle:

- Shows how ParaWorks bridges Slack/Gmail/Drive evidence and approved company
  knowledge into a single RAG serving corpus.
- Demonstrates production-minded design: deterministic test embeddings locally,
  a writer protocol for pgvector, and permission metadata carried through every
  indexed document.
- Keeps token cost under control by making indexing explicit and testable
  before introducing paid embedding providers.

Implemented scope:

- Added `DeterministicHashEmbeddingModel` for stable local embedding tests and
  smoke previews.
- Added `index_vector_documents` and `VectorIndexWriter` so the same pipeline
  can target the existing `PgVectorStore` adapter.
- Added `build_rag_index_documents` to collect all source chunks plus approved
  decision, history, and todo records.
- Added `POST /api/v1/rag/reindex` dry-run preview for validating indexing
  coverage without requiring live PostgreSQL in SQLite smoke mode.

Verification evidence:

- `uv run pytest backend/tests/test_rag_indexing.py -v` passed with 4 tests.
- `uv run pytest backend/tests -v` passed with 78 backend tests.
- `uv run ruff check backend/app/rag/embeddings.py backend/app/rag/indexing.py backend/app/api/v1/rag.py backend/tests/test_rag_indexing.py` passed.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-rag-vector-indexing.db`.
- Slack and Gmail mock sync created 3 source chunks; `POST /api/v1/rag/reindex`
  returned `dry_run=true`, `indexed_count=3`, `embedding_dimensions=16`, and
  `storage_backend=preview`.
- HTTP smoke returned 200 for `/dashboard`, `/review`, and `/search`.

## RAG Cost Optimization Update: Incremental Vector Indexing

Recorded on 2026-05-01.

Added the first explicit cost-control layer for paid embedding providers before
connecting OpenAI embeddings.

Portfolio angle:

- Shows product-aware AI engineering: the system avoids repeated embedding
  calls when Slack/Gmail/Drive sync runs over unchanged content.
- Makes cost savings observable through `skipped_count` and
  `saved_embedding_calls`, not just an internal implementation detail.
- Keeps future provider integration safer because the expensive boundary is
  already guarded by content hashing and index state.

Implemented scope:

- Added `VectorIndexState` and the `vector_index_states` table to track
  `document_id + embedding_model + content_hash`.
- Added stable `VectorDocument` content hashing.
- Added `index_changed_vector_documents` to skip unchanged documents, reindex
  changed documents, and persist successful index state.
- Extended `POST /api/v1/rag/reindex` dry-run responses with incremental cost
  signals: `skipped_count`, `skipped_document_ids`, and
  `saved_embedding_calls`.
- Documented that full-corpus re-embedding must not be the default path.

Verification evidence:

- `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_db_init.py -v`
  passed with 9 focused tests.
- `uv run pytest backend/tests -v` passed with 82 backend tests.
- `uv run ruff check backend/app/models/vector_index.py backend/app/rag/indexing.py backend/app/api/v1/rag.py backend/tests/test_rag_indexing.py`
  passed after Ruff import cleanup.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-incremental-vector-indexing.db`.
- Slack and Gmail mock sync created 3 source chunks; `POST /api/v1/rag/reindex`
  returned `incremental=true`, `indexed_count=3`, `skipped_count=0`, and
  `saved_embedding_calls=0` on a fresh index.
- HTTP smoke returned 200 for `/dashboard`, `/review`, and `/search`.

## RAG Infrastructure Update: Embedding Provider, pgvector Writes, Jobs, and Vector Retrieval

Recorded on 2026-05-01.

Completed the next RAG slice in the agreed order: provider boundary, pgvector
write mode, indexing job contract, and vector-capable retrieval.

Portfolio angle:

- Shows the expensive OpenAI embedding boundary is isolated, batch-oriented,
  usage-aware, and tested without live API calls.
- Demonstrates production safety: SQLite smoke mode cannot accidentally perform
  pgvector writes, while PostgreSQL mode requires an API key and explicit
  `dry_run=false`.
- Adds an operator-friendly job contract so indexing can move to Celery/Redis
  later without changing the product API.
- Makes the RAG answer path vector-ready while keeping local demos stable.

Implemented scope:

- Added `OpenAIEmbeddingModel` and `OpenAIEmbeddingConfig` using batched
  `/v1/embeddings` requests, `encoding_format=float`, optional dimensions, and
  usage tracking.
- Updated incremental indexing to batch only changed documents after content
  hash skip checks.
- Added OpenAI embedding settings and pgvector production write mode for
  `/api/v1/rag/reindex?dry_run=false`.
- Added `POST /api/v1/rag/reindex/jobs` backed by `SyncJob` for indexing job
  status and cost counters.
- Added optional vector-store retrieval in `answer_question_with_rag` and a
  guarded pgvector search adapter for Ask API.

Verification evidence:

- `uv run pytest backend/tests/test_embedding_provider.py backend/tests/test_rag_indexing.py -v`
  passed with provider and batch indexing tests.
- `uv run pytest backend/tests/test_rag_indexing.py::test_reindex_job_endpoint_records_indexing_job -v`
  passed.
- `uv run pytest backend/tests/test_rag_orchestrator_service.py::test_rag_service_can_answer_from_vector_store_matches -v`
  passed.
- `uv run pytest backend/tests -v` passed with 87 backend tests.
- `uv run ruff check backend/app/rag/embeddings.py backend/app/rag/indexing.py backend/app/api/v1/rag.py backend/app/api/v1/ask.py backend/app/agents/rag_orchestrator_agent/service.py backend/tests/test_embedding_provider.py backend/tests/test_rag_indexing.py backend/tests/test_rag_orchestrator_service.py`
  passed after Ruff import cleanup.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with
  `.tmp/paraworks-embedding-pgvector-job-retrieval.db`.
- Slack and Gmail mock sync created 3 source chunks; `POST /api/v1/rag/reindex/jobs`
  returned a `rag-index-*` job with `status=complete`, `indexed_count=3`,
  `embedding_request_count=1`, and `storage_backend=preview`.
- HTTP smoke returned 200 for `/dashboard`, `/review`, and `/search`.

## Product Observability Update: RAG Indexing Admin Panel

Recorded on 2026-05-01.

Moved RAG indexing cost-control signals into the Agent Operations/Admin surface
instead of the end-user Search screen.

Portfolio angle:

- Shows the cost optimization work in a demo-friendly way without polluting the
  final business-user product flow.
- Demonstrates product judgment: technical counters belong in admin
  observability, while Search remains focused on retrieval and evidence.
- Makes `indexed`, `skipped`, and `saved embedding calls` visible for operators
  so the team can prove incremental indexing is reducing provider calls.

Implemented scope:

- Added `GET /api/v1/rag/indexing/summary` with vector index state counts and
  latest `rag-index` jobs.
- Added RAG indexing types to the frontend API contract.
- Added a RAG indexing operations panel to `/agent-runs` with admin-only
  positioning and latest job counters.

Verification evidence:

- `uv run pytest backend/tests/test_rag_indexing.py::test_rag_indexing_summary_returns_latest_jobs_and_state_counts -v`
  passed.
- `uv run ruff check backend/app/api/v1/rag.py backend/tests/test_rag_indexing.py`
  passed.
- `uv run pytest backend/tests -v` passed with 88 backend tests.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-rag-indexing-observability.db`.
- Slack and Gmail mock sync created source chunks; `POST /api/v1/rag/reindex/jobs`
  returned `indexed_count=3`, `embedding_request_count=1`, and
  `status=complete`.
- `GET /api/v1/rag/indexing/summary` returned the latest `rag-index` job.
- HTTP smoke returned 200 for `/agent-runs`, `/search`, and `/dashboard`.

## RAG Infrastructure Update: pgvector Dev Path and Fake Embedding Integration Test

Recorded on 2026-05-01.

Added a safe developer path for validating real PostgreSQL + pgvector behavior
without putting live OpenAI calls in automated tests.

Portfolio angle:

- Shows production-readiness work beyond app code: runbooks, scripts,
  environment boundaries, and integration-test gates.
- Keeps provider cost and secret safety explicit by separating live manual
  checks from automated fake-embedding tests.
- Documents a real local blocker found during validation: Docker Postgres could
  not bind `127.0.0.1:5432` on this machine, and cleanup was handled with
  `docker compose down`.

Implemented scope:

- Added `docs/superpowers/runbooks/pgvector-dev.md` with startup, env,
  `dry_run=false`, fake integration test, port-conflict, and cost-policy notes.
- Added `scripts/start-pgvector-dev.ps1` for Postgres/Redis-backed local app
  startup without embedding secrets in the script.
- Added OpenAI embedding and pgvector search settings to `.env.example`.
- Added runbook/script tests and a skipped-by-default real pgvector integration
  test using `DeterministicHashEmbeddingModel`.

Verification evidence:

- `uv run pytest backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py -v`
  passed with 2 tests and skipped the real pgvector integration when
  `PARAWORKS_PGVECTOR_TEST_DATABASE_URL` was unset.
- `uv run ruff check backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py`
  passed.
- `uv run pytest backend/tests -v` passed with 90 backend tests and 1 skipped
  opt-in pgvector integration test.
- `npm.cmd run build` from `frontend` passed.
- `docker compose up -d postgres redis` pulled required images but failed to
  bind `127.0.0.1:5432`; partial containers were cleaned up with
  `docker compose down`.

## RAG Operations Update: Celery/Redis Indexing Job Contract

Recorded on 2026-05-01.

Moved RAG reindex jobs behind a Celery/Redis worker contract while preserving
deterministic eager execution for local smoke and tests.

Portfolio angle:

- Shows the difference between an API that does work synchronously and an
  operational job pipeline with queue, polling, and worker boundaries.
- Keeps cost controls intact: the worker executes the same incremental
  hash-skip pipeline before any embedding provider call.
- Demonstrates pragmatic local development: eager mode keeps SQLite smoke fast,
  while `CELERY_TASK_ALWAYS_EAGER=false` enables real Redis worker validation.

Implemented scope:

- Added Celery app construction with Redis broker/result backend and eager-mode
  settings.
- Added `rag.reindex` task plus `execute_rag_reindex_job` for testable job
  status transitions.
- Moved reindex execution logic out of the API route into
  `backend/app/rag/reindexing.py`.
- Updated `POST /api/v1/rag/reindex/jobs` to create a queued job first, then
  execute eagerly in local/test mode or enqueue for Celery in worker mode.
- Added `GET /api/v1/rag/reindex/jobs/{job_id}` for polling.
- Added `scripts/start-celery-worker.ps1` and documented worker mode in the
  pgvector runbook.

Verification evidence:

- `uv run pytest backend/tests/test_rag_indexing_tasks.py backend/tests/test_rag_indexing.py -v`
  passed with 17 focused tests.
- `uv run ruff check backend/app/tasks/celery_app.py backend/app/tasks/rag_indexing.py backend/app/rag/reindexing.py backend/app/api/v1/rag.py backend/tests/test_rag_indexing_tasks.py backend/tests/test_rag_indexing.py`
  passed.
- `uv run pytest backend/tests -v` passed with 95 backend tests and 1 skipped
  opt-in pgvector integration test.
- `npm.cmd run build` from `frontend` passed.
- Smoke server restarted with `.tmp/paraworks-celery-rag-indexing.db`.
- Slack and Gmail mock sync followed by `POST /api/v1/rag/reindex/jobs`
  returned `status=complete`; `GET /api/v1/rag/reindex/jobs/{job_id}` returned
  `indexed_count=3`; summary API returned one latest job.
- HTTP smoke returned 200 for `/agent-runs`, `/dashboard`, and `/search`.

## RAG Operations UX And Dev Path Hardening

Recorded on 2026-05-01.

Implemented the next recommended ParaWorks steps: Admin-facing async job UX,
normal-user search freshness UX, Celery queue-mode contract tests, and a
resilient pgvector local development path.

Portfolio angle:

- Shows product judgment around cost visibility: normal business users see
  company-memory freshness and evidence quality, while Admin/Ops users see
  embedding calls avoided, skipped documents, and job status details.
- Demonstrates operational maturity: RAG reindexing now has clearer
  `queued/running/complete/failed` UX, failure reason surfacing, and polling
  contracts.
- Shows practical backend discipline: queue mode is tested separately from eager
  local mode, so the API boundary stays safe when Redis/Celery is enabled.
- Reduces onboarding friction for collaborators by making pgvector host ports
  configurable instead of requiring tracked compose edits when `5432` is busy.

Implemented scope:

- Added `failure_reason` to RAG indexing job summaries for failed jobs.
- Added tests for failed-job detail responses and non-eager queue behavior.
- Updated `/agent-runs` with Korean operations copy, progress/status display,
  failure reason display, latest RAG jobs, and Admin-only cost counters.
- Updated `/search` with a non-technical company-memory freshness panel and
  removed token/cost/cache details from the normal user answer area.
- Added `PARAWORKS_POSTGRES_PORT` and `PARAWORKS_REDIS_PORT` compose defaults.
- Added `-PostgresPort` and `-RedisPort` to `scripts/start-pgvector-dev.ps1`.
- Documented alternate-port pgvector startup in the runbook.

Cost policy reinforced:

- Keep paid embedding and token-cost details in Admin/Ops screens.
- Give end users confidence signals without encouraging them to reason about
  provider internals.
- Preserve incremental indexing as the first cost gate before provider calls.

Verification evidence:

- Focused RAG/Celery tests passed with 20 tests.
- Focused Ruff passed for changed backend files.
- Full backend tests passed with 98 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- HTTP smoke confirmed health, RAG job creation/detail/summary, `/agent-runs`,
  and `/search`.
- HTML smoke confirmed the new Korean titles render and replacement characters
  are absent.
- Real Redis/Celery worker-mode smoke confirmed `queued -> complete` with
  `CELERY_TASK_ALWAYS_EAGER=false`.

## Connector Ingestion Contract

Recorded on 2026-05-01.

Started the real connector ingestion phase by defining the shared contract that
Slack, Gmail, Drive, Calendar, and future internal-document adapters must use.
Mock connectors now follow the same metadata shape expected from live OAuth
adapters.

Portfolio angle:

- Shows integration architecture beyond mock demos: external data sources enter
  through a stable `SourceEvent` + `ConnectorManifest` boundary.
- Supports 3-developer parallel work because Slack, Mail/Docs, and RAG workers
  can rely on one ingestion result shape instead of importing each other's code.
- Adds operational sync accounting with fetched, created, and skipped counts.
- Reinforces cost control before LLM/RAG work: duplicate source events are
  skipped before review extraction and before any downstream embedding.

Implemented scope:

- Added `ConnectorManifest` for connector type, display name, mode, auth type,
  OAuth scopes, sync strategy, and cost policy.
- Added a connector registry for integration metadata.
- Added `sync_connector_events` to centralize `SyncJob` creation, connector
  fetch, ingestion, duplicate skip counts, completion, and failure handling.
- Updated the integrations API to list manifest metadata and use the shared
  sync boundary.
- Updated `/integrations` to show connector manifest metadata, OAuth scope
  summaries, sync strategy, cost policy, fetched counts, and skipped counts in
  Korean.
- Updated `AGENTS.md` with connector ingestion rules for coding assistants.

Verification evidence:

- Focused connector tests passed with 12 tests.
- Focused Ruff passed for changed connector, ingestion, API, and test files.
- Full backend tests passed with 102 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- Smoke confirmed `/api/v1/integrations` returns 4 connector manifests,
  Slack history scopes, successful Slack sync with fetched/created/skipped
  counts, and `/integrations` renders Korean copy without replacement
  characters.

## Playwright Visual Smoke And RAG Permission Audit

Recorded on 2026-05-01.

Made frontend visual checking repeatable with Playwright and started the next
RAG permission/security hardening slice.

Portfolio angle:

- Adds a real visual regression workflow across desktop and mobile, not only
  HTTP smoke checks.
- Turns the previous Korean mojibake issue into an automated guardrail by
  checking key pages for Korean headings and broken replacement text.
- Strengthens RAG auditability without leaking hidden source content:
  end-users can see hidden match counts, while restricted source details remain
  filtered.
- Preserves connector ACL metadata on chunks so downstream RAG, review, and
  portfolio explanations can trace why content was visible or hidden.

Implemented scope:

- Installed `@playwright/test` and Chromium for local visual smoke.
- Added `frontend/playwright.config.ts`, `frontend/e2e/visual-smoke.spec.ts`,
  and `scripts/run-visual-smoke.ps1`.
- Added `npm run test:visual`.
- Rewrote `/dashboard` Korean copy to remove mojibake.
- Added `hidden_match_count` to search responses and `source_id` to visible
  search results.
- Added `source_ids` to Ask/RAG answers so visible answer citations are
  auditable by stable source identifiers.
- Preserved source id, permission level, participants, and connector raw
  metadata in `DocumentChunk.metadata_`.
- Updated `/search` to show hidden match counts without exposing hidden
  snippets or links.

Verification evidence:

- Focused permission/connector/Ask tests passed with 15 tests.
- Focused Ruff passed for changed backend search, ingestion, and tests.
- Full backend tests passed with 102 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- Playwright visual smoke passed with 10 Chromium desktop/mobile tests.
- Playwright initially failed because browser binaries were missing; installing
  Chromium made the check executable for future runs.

## Slack Live API Client Boundary

Recorded on 2026-05-01.

Started the real OAuth connector phase with a Slack Web API client boundary
while keeping mock mode as the default for demos and tests.

Portfolio angle:

- Shows the transition from mock connector harness to a live API-ready
  integration without leaking or requiring real workspace tokens.
- Keeps the connector architecture testable: Slack API behavior is verified
  with `httpx.MockTransport` and fake clients, never by calling Slack in tests.
- Preserves the ingestion contract: live Slack payloads still become
  `SourceEvent` records and flow through the same `sync_connector_events`
  pipeline as mock data.
- Reinforces cost and security discipline before LLM work: source deltas are
  fetched first, duplicates are skipped, and review/RAG boundaries remain
  evidence-driven.

Implemented scope:

- Added `SlackWebApiClient` for `conversations.history` bearer-token calls.
- Added cursor pagination and clear `SlackApiError` handling.
- Added `get_configured_connector` so Slack settings build a live connector
  only when token and channel ids are present.
- Updated `/api/v1/integrations/{connector_type}/sync` to use the configured
  connector factory while preserving mock fallback.
- Updated the Slack integration runbook with live env settings, scope
  requirements, no-secret policy, fake-client test policy, and cost/security
  notes.

Verification evidence:

- Focused Slack connector/factory/mock sync tests passed with 7 tests.
- Focused Ruff passed for the touched Slack connector, factory, integration
  endpoint, and tests.
- Full backend tests passed with 106 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- Playwright visual smoke passed with 10 Chromium desktop/mobile tests.

## Slack OAuth Installation Boundary

Recorded on 2026-05-01.

Added the first OAuth installation boundary for Slack while keeping real
workspace access opt-in and mock/demo behavior safe by default.

Portfolio angle:

- Demonstrates secure integration design beyond mock data: install URLs use
  signed state, OAuth code exchange is isolated behind a client boundary, and
  database records never store raw bot tokens.
- Shows production-minded defaults: `PARAWORKS_DEMO_MODE=true` keeps mock sync
  active even when local Slack credentials exist, preventing accidental API
  usage, private data ingestion, and surprise downstream indexing costs.
- Keeps the implementation testable without external services through
  `httpx.MockTransport`, fake access payloads, and a local token vault boundary.
- Creates a clean handoff point for the next developer slice: replacing the
  local vault with a managed secret store and wiring installed connections into
  sync.

Implemented scope:

- Added Slack OAuth settings and `.env.example` placeholders.
- Added `IntegrationConnection` to persist workspace metadata, scopes,
  `token_ref`, masked token, status, and non-sensitive metadata.
- Added `SlackOAuthStateSigner`, `SlackOAuthClient`, `LocalTokenVault`, install
  URL builder, and callback completion service.
- Added `/api/v1/integrations/slack/oauth/install-url` and callback endpoint.
- Updated connector factory so live Slack sync requires demo mode to be
  disabled as well as token/channel configuration.
- Updated Slack runbook with OAuth env, testing, cost, and security rules.

Verification evidence:

- RED test first: `backend/tests/test_slack_oauth.py` initially failed because
  `backend.app.connectors.slack_oauth` did not exist.
- Focused OAuth tests passed with 5 tests.
- Focused connector factory/mock/review/OAuth regression tests passed with 14
  tests.
- Focused Ruff passed for touched backend files and tests.
- Full backend tests passed with 112 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- Playwright visual smoke passed with 10 Chromium desktop/mobile tests.

## Slack OAuth UI Status

Recorded on 2026-05-01.

Wired the Slack OAuth installation boundary into the Integrations experience so
users can see whether Slack is connected, installable, or still waiting for
environment configuration.

Portfolio angle:

- Shows full-stack integration maturity: backend exposes sanitized connection
  state, and the frontend renders status/CTA without leaking raw tokens or
  `token_ref` values.
- Keeps the portfolio demo safe and cost-aware: mock sync remains usable when
  OAuth is not configured, and the UI clearly separates setup readiness from
  actual data ingestion.
- Adds visual smoke coverage so future UI work catches broken OAuth status
  cards on both desktop and mobile.

Implemented scope:

- Added `/api/v1/integrations/connections` to return connection status,
  workspace metadata, scopes, and masked tokens only.
- Added frontend API types for Slack OAuth install URLs and integration
  connections.
- Updated `/integrations` Slack card with connection status, setup guidance,
  and a safe Slack install CTA.
- Added Playwright coverage that the Slack OAuth status renders and does not
  expose common secret markers.

Verification evidence:

- RED backend test first: `/api/v1/integrations/connections` returned 404
  before implementation.
- RED visual smoke first: `[data-testid="slack-oauth-status"]` was missing
  before UI implementation.
- Focused backend connection API test passed.
- Python Ruff passed for touched backend files and tests.
- Full backend tests passed with 113 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- Playwright visual smoke passed with 12 Chromium desktop/mobile tests on fresh
  alternate ports.

## Installed Slack Sync Token Boundary

Recorded on 2026-05-01.

Connected installed Slack OAuth records to the sync connector factory without
putting raw tokens in the database or API responses.

Portfolio angle:

- Shows the handoff from OAuth installation to live ingestion readiness: the
  sync path can now build a `SlackConnector` from a stored connection record and
  a vault-resolved bot token.
- Preserves the cost guardrail: live Slack sync still requires
  `PARAWORKS_DEMO_MODE=false`, configured channel ids, and a resolvable vault
  token. Missing vault state falls back to mock instead of making unexpected
  external calls.
- Keeps the security story crisp for interviews: DB stores `token_ref` only,
  the vault resolves the secret at runtime, and sync responses never expose raw
  tokens or token references.

Implemented scope:

- Added `get_sync_connector` as the sync-time factory that can use installed
  Slack connections.
- Kept `get_configured_connector` as the legacy env-token path for local live
  experiments.
- Updated `/api/v1/integrations/{connector_type}/sync` to use the sync-time
  factory with DB context.
- Added tests for installed connection token resolution, missing-vault fallback,
  and sync endpoint secret non-exposure.
- Updated Slack runbook with installed sync selection and cost/security notes.

Verification evidence:

- RED factory test first failed because `get_sync_connector` did not exist.
- Focused connector/OAuth/mock sync tests passed with 13 tests.
- Python Ruff passed for touched backend files and tests.
- Full backend tests passed with 116 tests and 1 skipped pgvector integration
  test.
- Frontend production build passed.
- Playwright visual smoke passed with 12 Chromium desktop/mobile tests on fresh
  alternate ports.

## 2026-05-01 - Route Audit, Integrations Resilience, And Next 16 Upgrade

Audited the frontend after Slack OAuth status UI caused the integrations page to
degrade when optional status endpoints were unavailable on a stale backend.

Portfolio angle:

- Shows production-minded frontend hardening: core connector manifests now render
  independently from optional Slack OAuth connection metadata.
- Demonstrates end-to-end QA ownership: route coverage expanded from a narrow
  dashboard check to desktop/mobile smoke checks across dashboard, messages,
  review, knowledge, integrations, agent runs, and search.
- Keeps the cost story explicit: missing optional integration status APIs fail
  locally in UI state instead of triggering extra live connector, Slack, or
  embedding calls.

Implemented scope:

- Upgraded frontend dependencies to Next.js 16.2.4 and aligned ESLint with the
  ESLint 9 flat-config path.
- Fixed `/integrations` loading so Gmail, Google Drive, and Google Calendar
  modules stay visible when Slack OAuth status endpoints are not available.
- Removed the disabled Slack setup button from the normal demo path so the
  `Slack Agent 실행` action no longer wraps because of an unnecessary control.
- Added Playwright assertions for route-level rendering, mojibake prevention,
  missing application errors, and connector-card presence.

Verification evidence:

- Frontend lint passed with ESLint 9.
- Frontend production build passed on Next.js 16.2.4.
- Full backend tests passed with 116 tests and 1 skipped pgvector integration
  test.
- Playwright visual smoke passed with 22 Chromium desktop/mobile tests across
  all current MVP pages.
- `npm audit --audit-level=moderate` still reports a moderate advisory through
  Next's bundled PostCSS range; the suggested forced fix would downgrade Next and
  should not be applied.

## 2026-05-01 - Google OAuth Boundary For Gmail, Drive, And Calendar

Added a Google OAuth installation boundary for the three Google connector cards
without enabling live Google sync yet.

Portfolio angle:

- Shows disciplined integration sequencing: OAuth security and connection
  metadata land before live data ingestion.
- Demonstrates multi-connector architecture: Gmail, Drive, and Calendar share a
  signed-state OAuth boundary while preserving each connector's own scope set.
- Keeps the cost story visible: OAuth readiness does not trigger Google sync,
  LLM calls, or embedding work; future sync should fetch deltas and hash-check
  content before downstream agent work.

Implemented scope:

- Added `google_oauth.py` with signed state, install URL generation, callback
  completion, Google token exchange boundary, and sanitized persistence.
- Added backend settings for Google client id, client secret, redirect URI, and
  OAuth state secret.
- Extended the local token vault with a generic token kind so Google stores
  `local:<connector>:<account>:oauth` instead of a Slack-specific bot token ref.
- Added generic Google OAuth install/callback API routes under
  `/api/v1/integrations/{gmail|drive|calendar}/oauth/...`.
- Updated the Integrations UI to show OAuth status boxes for Gmail, Drive, and
  Calendar while keeping primary card actions focused on sync/agent execution.
- Added a Google integration runbook and a plan note for the implementation
  sequence.

Verification evidence:

- RED backend test first failed because `backend.app.connectors.google_oauth`
  did not exist.
- RED Playwright test first failed because `gmail-oauth-status` was missing.
- Focused Google/Slack OAuth backend tests passed with 12 tests.
- Frontend lint passed after the OAuth UI update.
- Playwright visual smoke passed with 24 Chromium desktop/mobile tests after
  Google OAuth readiness assertions were added.

## 2026-05-01 - Google Installed Sync Boundary

Connected installed Google OAuth records to the sync connector factory through a
live connector skeleton.

Portfolio angle:

- Shows the integration handoff after OAuth: installed Gmail, Drive, and Calendar
  connections can now become provider-specific sync connectors when demo mode is
  disabled.
- Demonstrates a merge-friendly split for three developers: each Google provider
  can now evolve behind the same `GoogleConnector` and `SourceEvent` contract.
- Keeps cost discipline explicit: demo mode remains mock-first, missing vault
  tokens fall back to mock, and future provider work must add cursor/hash delta
  checks before downstream agent or embedding calls.

Implemented scope:

- Added `backend/app/connectors/google.py` with Google API client skeletons and
  Gmail/Drive/Calendar `SourceEvent` mapping.
- Extended `get_sync_connector` to resolve installed Google connection tokens
  from the local vault when `PARAWORKS_DEMO_MODE=false`.
- Preserved mock fallback for demo mode and missing vault tokens.
- Added connector and factory tests for provider mapping, bearer-token headers,
  installed token resolution, demo fallback, and missing-vault fallback.
- Updated the Google integration runbook and added an implementation plan note.

Verification evidence:

- RED tests first failed because `backend.app.connectors.google` did not exist.
- Focused Google connector/factory tests passed with 13 tests.
- Python Ruff passed for the new Google connector, factory, and tests.
- Full backend tests passed with 129 tests and 1 skipped pgvector integration
  test.
- Frontend lint and production build passed.
- Playwright visual smoke passed with 24 Chromium desktop/mobile tests.
- The in-app browser showed Slack, Gmail, Drive, Calendar, and Google OAuth
  status blocks on `http://127.0.0.1:3000/integrations`.

## 2026-05-01 - Slack OAuth Callback UX And Redirect Audit

Hardened the Slack OAuth install path after a real Slack authorization attempt
failed with `redirect_uri did not match any configured URIs`.

Portfolio angle:

- Shows practical OAuth troubleshooting beyond mock integrations: local app
  routes, backend install URL generation, and third-party console settings must
  align exactly.
- Adds a safer user-facing callback page so OAuth failures are explained in
  Korean instead of surfacing a broken route or raw API response.
- Reinforces the security story: the callback UI shows sanitized workspace
  metadata only and regression tests block raw token, client secret, and
  `token_ref` leakage.

Implemented scope:

- Added `/integrations/slack/callback` frontend route.
- Forwarded Slack `code` and signed `state` to the backend callback endpoint.
- Rendered safe success, loading, and failure states for Korean business users.
- Documented that Slack App Redirect URLs must exactly match
  `SLACK_OAUTH_REDIRECT_URI`, including the `localhost` vs `127.0.0.1`
  distinction.

Cost/security note:

- OAuth installation itself does not sync Slack history, call an LLM, or create
  embeddings. Live sync remains gated by demo mode, channel ids, and vault token
  resolution so accidental installs do not create downstream token or embedding
  costs.

## 2026-05-02 - Slack OAuth Credential Status Guardrail

Added a clearer boundary between stored Slack connection metadata and actual
live-sync credential availability.

Portfolio angle:

- Shows a realistic integration hardening step: OAuth metadata in the database
  is not the same as a usable secret in the runtime vault.
- Prevents a misleading "connected" UI after local backend restarts, where the
  development in-memory vault may no longer hold the bot token.
- Keeps the secret boundary intact by exposing only `credential_status`, never
  raw tokens or `token_ref` values.

Implemented scope:

- Added sanitized `credential_status` to `/api/v1/integrations/connections`.
- Marked credentials as `available` only when the current backend process can
  resolve the local vault token.
- Updated the Integrations UI to show "재연결 필요" when connection metadata
  exists but the local development token is missing.
- Documented the local vault restart limitation in the Slack runbook.

Cost/security note:

- The UI now makes it harder to accidentally assume live Slack sync is ready.
  Real Slack ingestion remains gated by `PARAWORKS_DEMO_MODE=false`, channel
  ids, and a resolvable vault token before any downstream review, LLM, or
  embedding work can run.

## 2026-05-02 - Slack OAuth Reconnect UX

Closed the follow-up UX gap after adding credential availability checks: users
can now recover from local vault token loss directly from the Slack card.

Portfolio angle:

- Shows end-to-end product polish around real integration failure modes, not
  only the happy OAuth path.
- Keeps the primary sync/agent actions stable while placing the reconnect CTA
  inside the OAuth status area where it belongs.
- Adds desktop/mobile visual coverage for the `token missing -> Slack 재연결`
  state so the workspace name remains a single-line title and the recovery
  action stays readable.

Implemented scope:

- Added a `Slack 재연결` CTA when OAuth metadata exists but
  `credential_status` is missing.
- Kept the reconnect CTA out of the primary action row to avoid crowding
  `동기화` and `Slack Agent 실행`.
- Simplified the OAuth status title to the workspace name only.
- Kept the workspace title on one line with truncation; reconnect state is
  carried by the status pill, helper copy, and `Slack 재연결` CTA.

Cost/security note:

- Reconnection only refreshes the local credential boundary. It still does not
  sync Slack history or trigger downstream LLM/embedding work while demo mode is
  enabled.

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
- `af3c1f0 feat: add rag orchestrator agent`
- `2b377fb feat: add company memory ask ui`
- `15e1864 feat: add agent run observability`
- `b90a709 feat: persist rag agent runs`
- `870813c feat: promote approved review items`
- `84707e2 feat: add knowledge library`
- `6f6deab feat: use approved knowledge in rag`
- `3161dff feat: add agent run detail view`
- `9381bb1 fix: isolate smoke frontend cache`
- `aee1e04 feat: add agent run operations summary`
- `9f3a7b8 feat: add review vector orchestration foundations`
- `9e397f4 feat: add pgvector rag adapter`
- `feat: add rag vector indexing pipeline`
- `feat: add incremental vector indexing`
- `feat: add embedding provider and vector retrieval path`
- `feat: show rag indexing observability`
- `chore: document pgvector dev path`
- `feat: queue rag indexing jobs with celery`
- `feat: add slack live connector boundary`
- `feat: add slack oauth installation boundary`
- `feat: show slack oauth connection status`
- `feat: wire installed slack connection sync`
- `fix: harden frontend route smoke`
- `feat: add google oauth boundary`
- `feat: add google installed sync boundary`
