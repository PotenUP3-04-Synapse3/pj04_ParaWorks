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
