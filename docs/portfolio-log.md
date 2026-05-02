# ParaWorks Portfolio Log

Last updated: 2026-05-02

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

## 2026-05-02 - Slack Live Sync Error Handling

Started the first real Slack sync verification with `PARAWORKS_DEMO_MODE=false`
and confirmed the connector reaches Slack, but the configured channel is not
readable by the bot yet.

Portfolio angle:

- Shows real integration debugging beyond OAuth success: app installation,
  bot-channel membership, and channel ids are separate operational checks.
- Improves API resilience by turning Slack Web API failures into explicit 502
  responses instead of generic 500 errors.
- Keeps privacy intact during live testing by checking channel access and
  counts without printing Slack message bodies.

Implemented scope:

- Added a regression test for Slack API failure handling on the sync endpoint.
- Mapped `SlackApiError` from sync to an HTTP 502 with a clear detail message.
- Documented `channel_not_found` and `not_in_channel` troubleshooting in the
  Slack runbook.

Verification evidence:

- Live sync reached Slack and returned
  `Slack conversations.history failed: channel_not_found`.
- Follow-up channel access probes returned `not_in_channel` for sampled public
  channels, meaning the bot must be invited to a target channel or
  `SLACK_CHANNEL_IDS` must point to a bot-readable channel.

Cost/security note:

- The failed live sync did not trigger LLM or embedding work. Connector access
  is still the first cost gate; downstream review/RAG processing should only
  run after source access is valid and duplicate checks have completed.

## 2026-05-02 - Slack Live Sync Smoke Success

Completed the first successful live Slack sync path after adding the ParaWorks
bot to the configured Slack channel.

Portfolio angle:

- Demonstrates a real SaaS integration beyond mock data: OAuth, bot channel
  membership, Slack Web API access, ingestion, duplicate skipping, and agent
  review generation now work as one local smoke path.
- Shows privacy-aware verification: live Slack messages were synced into the
  local app, but terminal output only reported counts and status metadata, not
  message bodies.
- Reinforces cost discipline: source duplicate checks skipped unchanged Slack
  events before downstream review/agent work.

Verification evidence:

- Backend ran with `PARAWORKS_DEMO_MODE=false`.
- Slack `conversations.history` access check succeeded for the configured
  channel.
- `POST /api/v1/integrations/slack/sync` returned `status=complete`,
  `fetched_events=194`, `skipped_events=194`, and `created_review_items=0`.
- `POST /api/v1/integrations/slack/agent-review` returned
  `created_review_items=1` with the deterministic local Slack Agent.
- Agent run observability showed `total_runs=3`, `total_tokens=250`, and
  `estimated_cost_usd=0.000081`.

Next product step:

- Add a live sync readiness/status surface so users can see the active mode,
  configured channel id, last sync counts, and Slack API errors without opening
  terminal logs.
- Then continue with Review Queue promotion and RAG indexing over approved
  Slack-derived timeline/history candidates.

## 2026-05-02 - LangGraph Orchestrator Foundation

Moved the company memory orchestration foundation from a local sequential
runner to a real LangGraph `StateGraph` while keeping deterministic tests and
the existing agent contracts intact.

Portfolio angle:

- Shows the core ParaWorks architecture moving toward a true multi-agent
  orchestration layer instead of isolated demo agents.
- Keeps the three-developer split clean: Slack Agent, Mail/Docs Agent, and RAG
  Orchestrator can continue evolving behind shared `EvidencePacket` and
  review/RAG contracts.
- Adds a visible graph topology (`graph_mermaid`) that can later be reused in
  documentation, operations screens, or portfolio diagrams.

Implemented scope:

- Added `langchain>=1.2.0,<2.0.0` and `langgraph>=1.1.6,<2.0.0` to the backend
  dependencies. Local resolution installed `langchain==1.2.17` and
  `langgraph==1.1.10`.
- Replaced the local `AgentWorkflow.run()` loop with a compiled LangGraph
  `StateGraph`.
- Preserved append-only node audit behavior and exposed the graph as Mermaid.
- Added a workflow output marker for the cost policy:
  `delta_sync_hash_skip_evidence_budget`.

Cost/security note:

- This foundation still performs no paid LLM calls in tests. The next LLM
  integration should keep deterministic model doubles for CI, use delta sync
  and source-hash skips before agent calls, and persist `AgentRun` token/cost
  metadata for every production model call.

Verification evidence:

- `uv run pytest backend/tests/test_agent_orchestration.py -v` passed.
- `uv run pytest backend/tests/test_agent_runtime_contracts.py backend/tests/test_agent_registry.py backend/tests/test_agent_orchestration.py backend/tests/test_slack_agent.py backend/tests/test_mail_document_agent.py backend/tests/test_rag_orchestrator_agent.py -v` passed with 17 tests.

## 2026-05-02 - LangGraph Orchestration API

Exposed the company memory LangGraph workflow through backend API endpoints so
the frontend and operations screens can inspect orchestration status without
calling paid models.

Portfolio angle:

- Turns the orchestration foundation into a product-visible capability:
  backend clients can now read the active graph backend, node order, Mermaid
  topology, and cost guardrails.
- Adds a deterministic dry-run endpoint that proves the orchestration path
  executes end-to-end without invoking Slack, embeddings, or paid LLM APIs.
- Makes the architecture easier to explain in interviews: the graph can be
  shown as an API-backed execution contract instead of only code internals.

Implemented scope:

- Added `GET /api/v1/orchestration/company-memory` for workflow status,
  `node_names`, `graph_mermaid`, and cost policy flags.
- Added `POST /api/v1/orchestration/company-memory/dry-run` for deterministic
  execution over the same LangGraph workflow.
- Registered the orchestration router in the v1 API router.
- Added API tests for status and dry-run behavior.

Cost/security note:

- The status and dry-run endpoints report `paid_llm_calls_in_status_api=false`
  and `token_cost_usd=0`. This keeps operational visibility separate from
  model execution cost.

Verification evidence:

- `uv run pytest backend/tests/test_orchestration_api.py backend/tests/test_agent_orchestration.py backend/tests/test_agent_runs_api.py -v` passed with 9 tests.
- `uv run ruff check backend/app/api/v1/orchestration.py backend/app/api/v1/router.py backend/tests/test_orchestration_api.py backend/app/agent_runtime/orchestration.py backend/tests/test_agent_orchestration.py` passed.

## 2026-05-02 - Agent Runs LangGraph Operations Card

Connected the new LangGraph orchestration status API to the Agent Runs
operations page.

Portfolio angle:

- Makes the multi-agent orchestration architecture visible in the product UI:
  users can see the Company Memory graph backend, execution steps, and cost
  guardrails from the same page that tracks agent runs and token cost.
- Shows practical AI cost design in the interface: delta sync, source-hash
  skipping, evidence token budgeting, and blocked paid calls are presented as
  operational controls instead of buried implementation notes.
- Improves interview/demo storytelling by tying backend LangGraph work to a
  browser-verified admin experience.

Implemented scope:

- Added frontend API typing for `/api/v1/orchestration/company-memory`.
- Fetched orchestration status on `/agent-runs`.
- Added a LangGraph operations card with workflow steps and cost guardrails.
- Rechecked the page with Playwright screenshot verification after restarting
  the local smoke backend/frontend.

Cost/security note:

- The Agent Runs page only reads the status endpoint. It does not call the
  dry-run endpoint during render and does not trigger Slack, embeddings, or
  paid LLM calls.

Verification evidence:

- `npx eslint src/app/agent-runs/page.tsx src/lib/api/types.ts` passed.
- `npm run build` passed.
- `npx playwright screenshot --full-page http://127.0.0.1:3000/agent-runs ..\\.tmp\\agent-runs-langgraph-v2.png` completed.
- `npx playwright test e2e/visual-smoke.spec.ts -g "/agent-runs renders" --project=chromium-desktop` passed.

## 2026-05-02 - LangGraph Capture And Dry-Run UX

Captured the Company Memory LangGraph as reusable portfolio documentation and
added a zero-cost dry-run control to the Agent Runs operations page.

Portfolio angle:

- Adds a concrete architecture visual that can be used in the final portfolio:
  `docs/assets/company-memory-langgraph.svg` and
  `docs/assets/company-memory-langgraph.png`.
- Demonstrates that the LangGraph orchestrator is not only backend plumbing:
  the admin UI can now execute a deterministic dry-run and show the result.
- Shows cost discipline in product behavior: dry-run confirms orchestration
  order without Slack sync, embeddings, or paid LLM calls.

Implemented scope:

- Added a saved SVG graph and a Playwright-captured PNG for the Company Memory
  workflow.
- Added `OrchestrationDryRunResponse` frontend typing.
- Added a client-side `OrchestrationDryRun` control on `/agent-runs`.
- Added a Playwright regression test for the zero-cost dry-run UX.

Cost/security note:

- The dry-run calls `/api/v1/orchestration/company-memory/dry-run` and returns
  `token_cost_usd=0`. It does not read Slack message bodies, call embedding
  providers, or invoke external LLM APIs.

Verification evidence:

- `npx playwright screenshot --viewport-size=1280,720 file:///C:/Users/hanvv/Study/potenup3/pj04_ParaWorks/docs/assets/company-memory-langgraph.svg ..\\docs\\assets\\company-memory-langgraph.png` completed.
- `npx eslint src/app/agent-runs/page.tsx src/app/agent-runs/OrchestrationDryRun.tsx src/lib/api/types.ts e2e/orchestration.spec.ts` passed.
- `npm run build` passed.
- `npx playwright test e2e/orchestration.spec.ts --project=chromium-desktop` passed.
- `POST /api/v1/orchestration/company-memory/dry-run` returned four completed
  nodes and `token_cost_usd=0`.

## 2026-05-02 - LangGraph Agent Service Execution

Connected the Company Memory LangGraph workflow to the existing Slack,
Mail/Docs, and RAG agent services.

Portfolio angle:

- Moves the orchestrator from a visible dry-run foundation to a real execution
  path: LangGraph nodes now call agent services that persist `AgentRun`
  records and create review candidates.
- Preserves the three-developer split: Slack Agent and Mail/Docs Agent produce
  human-reviewable timeline/history candidates, while the RAG Orchestrator
  answers from company memory evidence.
- Demonstrates cost-aware orchestration: the real run endpoint is separate from
  status/dry-run and marked with `requires_explicit_run=true` so UI rendering
  never triggers hidden agent costs.

Implemented scope:

- Added `backend.app.agent_runtime.company_memory` for service-level Company
  Memory orchestration.
- Added reusable LangGraph workflow construction for custom node handlers.
- Added `POST /api/v1/orchestration/company-memory/run` as the explicit agent
  execution endpoint.
- Added tests proving Slack/Mail/RAG agent services run through LangGraph and
  persist the expected `AgentRun` and `ReviewItem` records.

Cost/security note:

- This run still uses deterministic local model implementations in tests. It
  creates estimated `AgentRun` token/cost metadata, but does not call external
  LLM providers unless a future production model adapter is explicitly wired.
- The endpoint is an explicit POST action, not part of page render/status
  polling, to avoid accidental token spend.

Verification evidence:

- `uv run pytest backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py backend/tests/test_agent_orchestration.py backend/tests/test_slack_agent.py backend/tests/test_mail_document_agent.py backend/tests/test_rag_orchestrator_service.py -v` passed with 18 tests.
- `uv run ruff check backend/app/agent_runtime/company_memory.py backend/app/agent_runtime/orchestration.py backend/app/agent_runtime/__init__.py backend/app/api/v1/orchestration.py backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py` passed.

## 2026-05-02 - Agent Candidate Bulk Approval

Added a safe Review Queue operation for approving agent-generated candidates
into Knowledge records.

Portfolio angle:

- Strengthens the human-in-the-loop company memory workflow: agent outputs do
  not enter durable Knowledge automatically, but reviewers can now approve
  agent candidates as a deliberate batch operation.
- Shows practical orchestration boundary design: Slack/Mail agents draft
  candidates, Review Queue gates them, and approved items become Knowledge that
  RAG can use.
- Demonstrates cost-aware workflow design because approval does not call LLMs
  or embeddings; it only promotes already-reviewed structured records.

Implemented scope:

- Added `POST /api/v1/review/approve-agent-candidates`.
- The endpoint only approves pending items that include an agent marker
  (`payload.agent_name`) and valid source evidence.
- Manual reviewer-created pending items remain pending.
- Added cost policy metadata indicating no paid LLM or embedding calls.

Cost/security note:

- The operation requires the human review state (`pending_review`) and skips
  invalid or manual items. It does not read secrets, call connectors, or trigger
  embedding/indexing work.

Verification evidence:

- `uv run pytest backend/tests/test_review_knowledge_promotion.py backend/tests/test_review.py backend/tests/test_knowledge_api.py backend/tests/test_rag_orchestrator_service.py -v` passed with 17 tests.
- `uv run ruff check backend/app/api/v1/review.py backend/tests/test_review_knowledge_promotion.py` passed.

## 2026-05-02 - Slack Runtime Status Surface

Added a Slack runtime status endpoint and connected it to the Integrations
operations UI.

Portfolio angle:

- Gives operators a direct view of Slack sync readiness: mock/live mode,
  configured channel ids, connection status, credential availability, and the
  latest sync job.
- Turns previous terminal-only Slack troubleshooting into product-visible
  observability.
- Reinforces cost discipline: the status lookup explicitly does not trigger
  sync, embeddings, or LLM calls.

Implemented scope:

- Added `GET /api/v1/integrations/slack/runtime-status`.
- The endpoint returns mode, configured channel ids, connection/credential
  status, latest Slack sync job metadata, and cost-policy flags.
- Added frontend `SlackRuntimeStatus` typing.
- Added a Slack operations status panel to `/integrations`.
- Extended Playwright smoke coverage to assert the runtime status panel is
  visible and still does not expose secrets.

Cost/security note:

- Runtime status is read-only. It reports existing metadata and does not fetch
  Slack messages, expose bot tokens, or invoke model/embedding work.

Verification evidence:

- `uv run pytest backend/tests/test_integration_runtime_status.py backend/tests/test_slack_oauth.py backend/tests/test_connector_factory.py -v` passed with 18 tests.
- `uv run ruff check backend/app/api/v1/integrations.py backend/tests/test_integration_runtime_status.py` passed.
- `npx eslint src/app/integrations/page.tsx src/lib/api/types.ts e2e/visual-smoke.spec.ts` passed.
- `npm run build` passed.
- `npx playwright test e2e/visual-smoke.spec.ts -g "integrations page shows Slack OAuth" --project=chromium-desktop` passed.

## 2026-05-02 - Google Runtime Status Surface

Extended connector runtime observability from Slack to Gmail, Google Drive, and
Google Calendar.

Portfolio angle:

- Makes Google integration readiness inspectable in the product UI before the
  team invests in deeper live connector work.
- Aligns all major connectors around the same operational contract: mode,
  connection state, credential state, account/channel context, latest sync, and
  no-cost status lookup.
- Reduces debugging dependence on terminal logs for OAuth and sync issues.

Implemented scope:

- Added `GET /api/v1/integrations/{gmail|drive|calendar}/runtime-status`.
- Added backend tests for Google runtime status and unknown connector handling.
- Added frontend `GoogleRuntimeStatus` typing.
- Added a Google operations status panel to `/integrations`.
- Extended Playwright smoke coverage to assert the Google runtime panel is
  visible.

Cost/security note:

- Google runtime status is read-only. It does not call Google APIs, fetch mail
  or documents, trigger embeddings, or invoke LLMs. It also avoids exposing raw
  refresh tokens or token references.

Verification evidence:

- `uv run pytest backend/tests/test_integration_runtime_status.py -v` passed.
- `uv run ruff check backend/app/api/v1/integrations.py backend/tests/test_integration_runtime_status.py` passed.
- `npx eslint src/app/integrations/page.tsx src/lib/api/types.ts e2e/visual-smoke.spec.ts` passed.
- `npm run build` passed.
- `npx playwright test e2e/visual-smoke.spec.ts -g "Google connector cards" --project=chromium-desktop` passed.

## 2026-05-02 - Execution Cost Plan And Skip Reasons

Why it matters:

- The company-memory graph should not call every agent just because a user
  pressed run. Slack, mail/document, and RAG agents now receive an execution
  cost plan before the graph enters the expensive service nodes.
- The cost plan records each agent's `run` or `skip` decision, the reason, and
  deterministic input/output token estimates. This keeps the demo portfolio
  honest about API cost instead of hiding cost behind orchestration language.
- Empty Slack evidence, empty mail/document evidence, and empty questions now
  skip their agent calls and avoid creating misleading `AgentRun` records.

Implemented scope:

- Added a company-memory cost plan builder to the LangGraph runtime.
- Threaded `cost_plan` through graph state and orchestration outputs.
- Guarded Slack review drafting, mail/document review drafting, and RAG answer
  generation with per-agent skip decisions.
- Added regression coverage for both run and skip paths.

Cost/security note:

- This is a local deterministic estimate. It does not call an embedding model,
  LLM, Slack, Google, or external API.
- The skip path is intentionally conservative: if there is no evidence or no
  user question, the runtime spends zero model tokens for that agent.

Verification evidence:

- `uv run pytest backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py backend/tests/test_agent_runs_api.py -v` passed.
- `uv run ruff check backend/app/agent_runtime/company_memory.py backend/tests/test_company_memory_orchestration_service.py` passed.

## 2026-05-02 - Runtime Status Secret Redaction

Why it matters:

- Integration status pages are useful for debugging live Slack and Google
  setup, but sync failure messages can accidentally include access tokens,
  refresh tokens, token references, or OAuth client secrets.
- Runtime status APIs now redact secret-like strings before returning
  `latest_sync.message` to the frontend.
- The original sync record is left intact for server-side diagnosis; redaction
  happens at the API boundary where user-facing exposure risk exists.

Implemented scope:

- Added `redact_secret_text` for Slack token, token reference, refresh token,
  and client secret patterns.
- Applied redaction to integration runtime status sync messages.
- Added regression tests for Slack and Google runtime status secret leakage.

Cost/security note:

- The redaction path is local string processing. It does not call connector
  APIs or LLMs.
- This reduces the risk of leaking sensitive operational values through the
  Korean-first dashboard during live connector testing.

Verification evidence:

- `uv run pytest backend/tests/test_integration_runtime_status.py -v` passed.
- `uv run ruff check backend/app/api/v1/integrations.py backend/app/core/redaction.py backend/tests/test_integration_runtime_status.py` passed.

## 2026-05-02 - Portfolio Case Study Draft

Why it matters:

- The project now has enough architecture and implementation evidence to be
  presented as more than a UI clone or basic RAG demo.
- A dedicated case study helps explain the engineering value: multi-agent
  ownership, LangGraph orchestration, evidence-first review, pgvector-ready RAG,
  cost controls, and connector security boundaries.

Implemented scope:

- Added `docs/portfolio-case-study.md`.
- Structured the story around problem, architecture, agent ownership, cost
  optimization, security/review boundaries, frontend experience, verification,
  and a resume bullet draft.
- Referenced the saved LangGraph graph capture assets.

Verification evidence:

- Documentation-only change reviewed against `AGENTS.md` and the current
  implementation history.

## 2026-05-02 - Playwright Sync Metric Selector Hardening

Why it matters:

- The integration smoke test failed because a broad `Fetched` text lookup also
  matched lower-case `fetched=` text inside recent sync status messages.
- The page itself rendered correctly, but the test selector was too fragile for
  a screen that intentionally shows both metric labels and sync log summaries.

Implemented scope:

- Added `data-testid="sync-result-metrics"` to the integration sync result
  metric grid.
- Scoped Playwright metric assertions to that grid and used exact text
  matching for `Fetched`, `Review items`, and `Skipped`.

Verification evidence:

- `npx eslint src/app/integrations/page.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 14/14 tests.

## 2026-05-02 - Liquid Glass Frontend Refresh

Why it matters:

- ParaWorks needed a more memorable portfolio-facing visual identity without
  losing its Slack-like business workspace ergonomics.
- The refresh follows Apple Liquid Glass guidance by treating navigation,
  search, and primary controls as a floating functional layer while keeping
  content surfaces readable.

Implemented scope:

- Reworked global visual tokens for translucent panels, glass controls,
  stronger depth shadows, subtle structured background light, and accessibility
  fallbacks for reduced transparency or increased contrast.
- Refreshed `AppShell` with a floating glass sidebar, mobile glass toolbar,
  glass search command surface, and stained-glass primary agent action.
- Applied global surface behavior so existing cards and panels inherit the new
  material without rewriting every page.

Cost/security note:

- This is a frontend-only visual change. It does not trigger connector sync,
  embeddings, or LLM calls.
- Status colors and operational labels remain visible so the design stays
  useful for business users and live connector debugging.

Verification evidence:

- `npm run build` passed.
- `npx eslint src/components/layout/AppShell.tsx` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 14/14 tests.
- In-app browser screenshot review checked `/dashboard` and `/integrations` at
  the current viewport.

## 2026-05-02 - Liquid Glass Intensity Pass

Why it matters:

- The first Liquid Glass refresh improved the theme, but still read closer to a
  soft translucent dashboard than an iOS-style glass system.
- This pass pushed the material closer to Liquid Glass by adding stronger
  refraction edges, reflective highlights, deeper blur/saturation, and floating
  dock-like navigation surfaces.

Implemented scope:

- Intensified global glass tokens, shadows, background light sheets, and
  refractive edge overlays.
- Added shared pseudo-element highlights to liquid surfaces, dark rails,
  controls, and primary stained-glass actions.
- Upgraded the mobile toolbar into a rounded glass slab and made the desktop
  sidebar/top search feel more like floating system chrome.
- Restored `--workspace-rail-active` to a readable text color after visual QA
  showed page eyebrow labels becoming too faint.

Verification evidence:

- `npx eslint src/components/layout/AppShell.tsx` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 14/14 tests.
- `npm run build` passed.
- In-app browser screenshot review checked `/dashboard` after the intensity
  pass and contrast fix.

## 2026-05-02 - Dark Liquid Glass Mode

Why it matters:

- Browser QA showed the light Liquid Glass theme was still too bright for
  dense business screens, reducing text readability.
- ParaWorks now defaults to a darker, higher-contrast Liquid Glass experience
  while preserving a light mode toggle for comparison and future demos.

Implemented scope:

- Added `data-theme` based dark/light glass modes with a pre-hydration script
  to avoid a bright first paint.
- Added persistent theme toggles in the sidebar and mobile toolbar.
- Reworked dark-mode glass tokens, page background, panels, controls, status
  surfaces, and hard-coded text/background overrides so existing pages remain
  consistent.
- Added Playwright coverage for switching between dark and light glass modes.

Verification evidence:

- `npx eslint src/app/layout.tsx src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 15/15 tests.
- `npm run build` passed.
- In-app browser screenshot review checked `/dashboard` and `/integrations` in
  dark Liquid Glass mode.

## 2026-05-02 - Gray Purple Dark Glass Palette

Why it matters:

- User feedback clarified that the dark mode should not feel like a navy SaaS
  dashboard. The target palette is charcoal gray first, with white glass glow
  and a Slack-like deep purple accent group.
- This keeps the Liquid Glass look vivid while making the workspace calmer,
  more business-like, and more consistent.

Implemented scope:

- Replaced the dark-mode navy/blue/cyan token group with charcoal gray,
  white-glow, and deep purple glass tokens.
- Updated dark page background, glass controls, panels, primary actions,
  shadows, and hard-coded color overrides to reduce blue cast.
- Verified `/dashboard` and `/integrations` visually in the in-app browser,
  including OAuth/status panel contrast.

Verification evidence:

- `npx eslint src/app/layout.tsx src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 15/15 tests.
- `npm run build` passed.

## 2026-05-02 - Dark Glass Consistency QA Fix

Why it matters:

- Browser QA found that the integrations page still had inconsistent Liquid
  Glass details: cards looked too milky, the language segment active state felt
  flat, some OAuth text used old hard-coded colors, and sync buttons did not
  belong to the same glass system.
- The dark gray and deep purple palette needs consistent contrast and material
  behavior across controls, cards, and status panels.

Implemented scope:

- Added a `liquid-segment-active` material for KO/EN and active mobile/sidebar
  navigation states.
- Added `integration-glass-card` to reduce unnatural white opacity on
  integration cards and keep their glass tone closer to the primary purple
  action.
- Reworked integration sync and agent buttons to use `liquid-primary` and
  `liquid-control` instead of flat dark/white button styles.
- Replaced OAuth status hard-coded text colors with theme token colors so
  contrast stays consistent in dark mode.

Verification evidence:

- In-app browser screenshot review checked `/integrations` in dark mode.
- `npx eslint src/components/layout/AppShell.tsx src/app/integrations/page.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 15/15 tests.
- `npm run build` passed.

## 2026-05-02 - Integration Runtime Glass Consistency

Implemented scope:

- Unified the `/integrations` task stream panel with the same
  `integration-glass-card` material used by the connector cards.
- Replaced Slack/Google runtime status hard-coded text colors with
  `--ink-strong` so dark-mode contrast follows the Liquid Glass token system.
- Added a reusable `glass-row` surface for runtime rows and sync metrics,
  keeping nested glass elements in the same gray-purple material family.
- Changed runtime mode pills to `liquid-control` so they visually align with
  the top floating controls and primary dark-mode button treatment.

Verification evidence:

- In-app browser screenshot review checked `/integrations` in dark mode.
- `npx eslint src/app/integrations/page.tsx src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`
  passed with 15/15 tests.
- `npm run build` passed.

## 2026-05-02 - Cross-Viewport Theme Token Audit

Implemented scope:

- Compared `/integrations` across desktop/mobile and dark/light modes with
  Playwright computed-style checks.
- Replaced desktop shell hard-coded `text-white/*`, `border-white/*`, and
  white hover states with `--shell-*` theme tokens.
- Added a `shell-rail` glass material so the desktop sidebar becomes a light
  frosted rail in light mode and gray-purple glass in dark mode.
- Aligned mobile language hover states with `--glass-control-strong` instead
  of hard-coded white opacity.
- Added a Playwright regression test that verifies shell chrome changes
  tokens across desktop and mobile theme modes.

Verification evidence:

- Playwright computed-style audit confirmed desktop sidebar changes from
  dark `rgba(18, 17, 21, 0.62)` to light `rgba(255, 255, 255, 0.54)`.
- `npx eslint src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 32/32 tests.
- `npm run build` passed.

## 2026-05-02 - Light Gray Deep Purple Palette

Implemented scope:

- Toned down the light-mode foundation from bright white glass to warm light
  gray glass surfaces.
- Shifted light-mode shell, active accents, primary controls, and outlines
  toward ParaWorks deep purple (`#4a154b`) for stronger brand consistency.
- Reduced mint/blue emphasis in the light-mode background, controls, cards,
  and rows so the UI reads as one coherent gray-purple material system.
- Kept dark-mode tokens unchanged while preserving the shared Liquid Glass
  component structure.

Verification evidence:

- In-app browser screenshot review checked `/integrations` in light mode.
- Playwright computed-style audit confirmed light shell `rgba(228, 225, 235, 0.74)`
  and primary action `rgba(74, 21, 75, 0.9)`.
- `npx eslint src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 32/32 tests.
- `npm run build` passed.

## 2026-05-02 - Light Purple Palette Adjustment

Implemented scope:

- Shifted the light-mode accent system from deep purple to soft lavender and
  light purple while keeping the gray glass foundation.
- Separated active segment behavior so light mode uses dark text on lavender
  glass and dark mode keeps the existing high-contrast deep purple treatment.
- Updated light-mode shell, surface, control, card, and row tint gradients to
  reduce heavy purple saturation and keep the UI calmer.

Verification evidence:

- In-app browser screenshot review checked `/integrations` in light mode.
- Playwright computed-style audit confirmed light shell `rgba(232, 226, 241, 0.76)`
  and primary action `rgba(183, 154, 221, 0.9)`.
- `npx eslint src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 32/32 tests.
- `npm run build` passed.

### Agent Cost Budget Guardrails

- Added a reusable agent runtime cost decision that estimates input/output
  token cost before execution and returns `run`, `skip`, or `use_cache`.
- Connected the company memory LangGraph orchestration cost plan to a per-run
  budget limit so large evidence windows can be skipped before calling an LLM.
- Preserved explicit skip reasons such as `no_slack_evidence`,
  `empty_question`, and `budget_exceeded` so the UI/API can explain why an
  agent did or did not run.
- Kept cache hits as a first-class policy outcome so future prompt/result cache
  reuse can avoid paid calls even when the potential token window is large.

Portfolio angle:

- Demonstrates that ParaWorks treats LLM cost as an architecture concern, not a
  post-hoc dashboard metric.
- Gives the three-agent split a shared budget contract, making independently
  developed Slack, Mail/Document, and RAG agents easier to merge safely.
- Supports the final product goal of multi-agent orchestration while protecting
  against expensive repeated sync and re-vectorization patterns.

Verification evidence:

- Added RED tests first for over-budget skip behavior and cache-first budget
  decisions.
- `uv run pytest backend/tests/test_agent_runtime_contracts.py backend/tests/test_company_memory_orchestration_service.py`
  passed with 9/9 tests.
- `uv run ruff check backend/app/agent_runtime backend/tests/test_agent_runtime_contracts.py backend/tests/test_company_memory_orchestration_service.py`
  passed after applying automatic import cleanup.
- `uv run pytest backend/tests/test_agent_runtime_contracts.py backend/tests/test_company_memory_orchestration_service.py backend/tests/test_agent_orchestration.py backend/tests/test_agent_runs_api.py`
  passed with 16/16 tests.

### Agent Budget Observability

- Exposed the default per-run agent budget and the supported budget actions
  (`run`, `skip`, `use_cache`) through the company memory orchestration status
  and run APIs.
- Updated the Agent Operations page so operators can see the active per-run
  budget directly beside the LangGraph orchestration and cost guardrail status.
- Added frontend fallback handling so the operations page stays renderable even
  if a running backend still returns the older cost policy shape.
- Kept status API calls free of paid LLM calls while still showing enough budget
  metadata to explain cost behavior before a real run.

Portfolio angle:

- Shows an operator-facing cost control loop: policy, API contract, UI
  visibility, and tests are aligned.
- Makes cost optimization demonstrable during portfolio walkthroughs without
  requiring real paid model calls.

Verification evidence:

- Added API tests first for budget metadata visibility.
- `uv run pytest backend/tests/test_orchestration_api.py` passed with 3/3 tests.
- `uv run ruff check backend/app/api/v1/orchestration.py backend/tests/test_orchestration_api.py`
  passed.
- `npx eslint src/app/agent-runs/page.tsx src/lib/api/types.ts` passed.
- `npm run build` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 32/32 tests after adding the fallback.

### Global Search Bar Activation

- Converted the desktop sidebar search and floating top search from static
  glass UI into real search forms.
- Both search bars now submit to `/search?q=...`, preserving the Liquid Glass
  visual treatment while making the controls keyboard-friendly.
- Updated the Company Memory search page to read the `q` URL parameter, hydrate
  the input with that query, and immediately run the existing RAG/search flow.
- Added Korean and English placeholders to the shell dictionary so both locales
  show natural search copy.

Portfolio angle:

- Turns visible UX affordances into working product paths without adding a new
  backend surface.
- Demonstrates integration between shell navigation, URL-driven state, and the
  existing RAG/search agent flow.

Verification evidence:

- Added Playwright tests first for sidebar and top search submission.
- Confirmed both new tests failed before implementation because the inputs did
  not exist.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop -g "search submits"`
  passed with 2/2 tests.
- `npx eslint src/components/layout/AppShell.tsx src/app/search/page.tsx src/lib/i18n/dictionary.ts e2e/visual-smoke.spec.ts`
  passed.
- `npm run build` passed after wrapping `useSearchParams` usage in a Suspense
  boundary.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 34/34 executed tests and 2 expected mobile skips.

### Google OAuth Callback Activation

- Added a generic backend Google OAuth callback route at
  `/api/v1/integrations/google/oauth/callback` that reads the signed state to
  determine whether the returning connection is Gmail, Google Drive, or
  Calendar.
- Added the frontend `/integrations/google/callback` route so Google Cloud's
  shared redirect URI can complete OAuth installs and persist connection
  metadata.
- Kept raw Google access/refresh tokens and internal token refs out of the UI,
  matching the Slack OAuth redaction pattern.
- Added explicit visual coverage for Gmail and Google Drive connect CTAs when
  OAuth is configured, while keeping those CTAs outside the primary sync/action
  row.

Portfolio angle:

- Moves Google integration from a readiness boundary into a real OAuth install
  loop for Gmail and Drive.
- Shows secure connector UX: signed state routing, token redaction, safe local
  error states, and post-callback connection metadata.

Verification evidence:

- Added RED tests first for missing generic Google callback API and missing
  frontend callback route.
- `uv run pytest backend/tests/test_google_oauth.py` passed with 6/6 tests.
- `uv run ruff check backend/app/api/v1/integrations.py backend/tests/test_google_oauth.py`
  passed.
- `npx eslint src/app/integrations/google/callback/page.tsx src/app/integrations/google/callback/GoogleCallbackClient.tsx src/app/integrations/page.tsx e2e/visual-smoke.spec.ts`
  passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop -g "Google"`
  passed with 4/4 tests.
- `npm run build` passed and listed `/integrations/google/callback`.
- `uv run pytest backend/tests/test_google_oauth.py backend/tests/test_integration_runtime_status.py backend/tests/test_google_connector.py`
  passed with 16/16 tests.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 40/40 executed tests and 2 expected mobile skips.

### Light Deep Purple Theme Tuning

- Replaced the light mode lavender palette with a brighter deep-purple family
  while keeping the base surface tone in light gray.
- Updated light-mode shell, primary action, active segment, glass control, card,
  and row tint gradients so the theme reads closer to Slack-adjacent deep
  purple rather than soft lavender.
- Preserved dark mode tokens and the existing Liquid Glass structure.

Portfolio angle:

- Shows iterative product design judgment: visual direction was adjusted from
  soft lavender to a more confident business-oriented light deep-purple tone
  after browser review.
- Keeps the design system tokenized so future UI changes can be made without
  hardcoding page-by-page color fixes.

Verification evidence:

- `npm run build` passed.
- `npx eslint src/components/layout/AppShell.tsx e2e/visual-smoke.spec.ts`
  passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile`
  passed with 40/40 executed tests and 2 expected mobile skips.

## Demo Login And Admin Permission Foundation

What changed:

- Added a demo auth API with `admin@paraworks.com` plus three employee
  accounts so portfolio demos can switch between admin, internal employee, and
  public-only permission scopes.
- Added `/login` for demo account switching and `/admin` for an admin-only
  user/permission console.
- Aligned the frontend API client with the selected demo user so search, ask,
  and admin APIs use the same permission header instead of hardcoded admin or
  viewer behavior.
- Updated Playwright to use `http://localhost:3000` by default because Next dev
  hydration failed on `127.0.0.1` in this local environment.

Verification evidence:

- `uv run pytest backend/tests/test_auth_api.py backend/tests/test_search_permissions.py backend/tests/test_ask_api.py backend/tests/test_agent_runs_api.py backend/tests/test_knowledge_api.py backend/tests/test_integration_runtime_status.py`
  passed with 20 tests.
- `npx eslint src/app/login/page.tsx src/app/admin/page.tsx src/app/search/page.tsx src/components/layout/AppShell.tsx src/lib/api/client.ts src/lib/api/types.ts src/lib/i18n/dictionary.ts e2e/visual-smoke.spec.ts playwright.config.ts`
  passed.
- `npm run build` passed.
- `npx playwright test e2e/visual-smoke.spec.ts` passed with 50 executed tests
  and 2 expected mobile skips after starting the local smoke backend with a
  SQLite dev DB because the local PostgreSQL password was rejected.

## Workspace Glass Card Consistency

What changed:

- Promoted the integrations page glass-card treatment into shared
  `--card-glass-*` and `--row-glass-*` design tokens.
- Aligned `integration-glass-card`, `liquid-surface`, general `bg-white` cards,
  and `glass-row` helper panels so dark and light modes use the same card
  background, border, highlight, and shadow model.
- Verified computed browser styles for integration, dashboard, and search cards
  in both dark and light modes.

Verification evidence:

- `npm run build` passed.
- `npx playwright test e2e/visual-smoke.spec.ts` passed with 50 executed tests
  and 2 expected mobile skips.

## Pgvector Dev Environment Hardening

What changed:

- Added Postgres and Redis healthchecks to the local Docker stack and made the
  pgvector helper detect an occupied host `5432` before falling back to `55432`.
- Added `scripts/check_pgvector_dev.py` so developers can verify the vector
  extension, vector table, and app indexing state table without guessing whether
  the local DB is ready.
- Added a `-SkipApp` path for DB-only setup, documented the `127.0.0.1` database
  URL convention, and kept frontend dev URLs on `localhost` for stable Next.js
  browser testing.
- Fixed pgvector metadata writes by serializing metadata as JSON before casting
  to `jsonb` in PostgreSQL.
- Made the live pgvector integration test use unique document IDs so incremental
  indexing state does not hide regressions between repeated runs.

Portfolio angle:

- Shows production-minded local infrastructure work: the vector DB path is now
  reproducible, testable, and safer when another local PostgreSQL instance is
  already running.
- Strengthens the RAG story for interviews because ParaWorks can demonstrate
  SQLite smoke mode for quick demos and PostgreSQL + pgvector for the real
  retrieval architecture.
- Keeps future embedding/token costs under control by preserving the incremental
  indexing path while validating that only changed documents need to be written.

Verification evidence:

- `uv run python scripts/check_pgvector_dev.py --database-url postgresql+psycopg://paraworks:paraworks@127.0.0.1:55432/paraworks --expect-app-schema`
  passed against the local pgvector container with vector extension `0.8.2`.
- `uv run pytest backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py backend/tests/test_pgvector_store.py backend/tests/test_rag_indexing.py backend/tests/test_rag_indexing_tasks.py backend/tests/test_rag_orchestrator_service.py backend/tests/test_vector_retriever.py -v`
  passed with 37 tests.
- `docker compose config` passed.
- `uv run ruff check backend/app/rag/pgvector_store.py scripts/check_pgvector_dev.py backend/tests/test_pgvector_store.py backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py backend/tests/test_rag_indexing_tasks.py`
  passed.

## Embedding Cost Preflight Guard

What changed:

- Added a preflight embedding budget gate before paid OpenAI embedding calls in
  the RAG indexing path.
- Added environment-controlled pricing and budget settings:
  `OPENAI_EMBEDDING_INPUT_COST_PER_1M_TOKENS` and
  `RAG_EMBEDDING_MAX_ESTIMATED_COST_USD`.
- Exposed the active RAG indexing cost policy through
  `/api/v1/rag/indexing/summary` and surfaced it in the company memory search
  freshness panel.
- Preserved incremental hash skip behavior so unchanged documents continue to
  avoid embedding requests entirely.

Portfolio angle:

- Shows cost-aware AI engineering: ParaWorks estimates changed-document
  embedding cost before a provider request can spend money.
- Makes the system easier to operate in a three-developer workflow because the
  active budget policy is visible through the API and frontend instead of living
  only in `.env`.
- Strengthens the product story that RAG quality and token-cost discipline are
  designed together, not treated as separate cleanup work.

Verification evidence:

- Added a RED test that failed because the embedding budget exception did not
  exist, then implemented the gate until the test passed.
- Added a RED test for the missing indexing summary `cost_policy`, then exposed
  the API field until the test passed.
- `uv run pytest backend/tests/test_pgvector_dev_runbook.py backend/tests/test_pgvector_integration.py backend/tests/test_pgvector_store.py backend/tests/test_rag_indexing.py backend/tests/test_rag_indexing_tasks.py backend/tests/test_rag_orchestrator_service.py backend/tests/test_vector_retriever.py backend/tests/test_embedding_provider.py -v`
  passed with 39 tests.
- `uv run ruff check backend/app/rag/indexing.py backend/app/rag/reindexing.py backend/app/api/v1/rag.py backend/app/core/config.py backend/tests/test_rag_indexing.py`
  passed.
- `npx eslint src/app/search/page.tsx src/lib/api/types.ts` passed.
- `npm run build` passed.

## RAG Reindex Approval UX

What changed:

- Extended dry-run reindex responses with `embedding_budget`, including changed
  document count, estimated input tokens, estimated cost, budget limit, and the
  resulting budget action.
- Kept dry-run free and non-blocking: over-budget dry-runs return a warning
  preview instead of calling the embedding provider.
- Added a RAG reindex approval panel to `/agent-runs` so operators can run a
  cost preview before approving `dry_run=false` execution.
- Added desktop and mobile Playwright coverage for the preview -> approved run
  interaction.

Portfolio angle:

- Turns backend cost guardrails into an operator-facing workflow, which is more
  compelling than a hidden environment variable.
- Shows responsible AI product design: paid embedding work requires a visible
  estimate and explicit approval.
- Helps a three-developer team integrate safely because RAG indexing behavior is
  observable and test-covered from API to browser.

Verification evidence:

- Added RED tests for missing dry-run `embedding_budget`, then implemented the
  preview response until they passed.
- `uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_rag_indexing_tasks.py -v`
  passed with 22 tests.
- `uv run ruff check backend/app/rag/indexing.py backend/app/rag/reindexing.py backend/tests/test_rag_indexing.py`
  passed.
- `npx eslint src/app/agent-runs/page.tsx src/app/agent-runs/RagReindexControl.tsx src/lib/api/types.ts e2e/visual-smoke.spec.ts`
  passed.
- `npm run build` passed.
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop --project=chromium-mobile -g "agent operations previews"`
  passed with 2 tests.

## Google Live Collection Hardening

What changed:

- Upgraded the live Google Web API client so Gmail and Google Drive collection
  can read beyond the first API page.
- Gmail now performs a lightweight list -> detail hydration flow: list message
  ids first, then fetch metadata-only details for `Subject`, `From`, and
  `Date`.
- Google Drive file listing now requests `nextPageToken` and follows it while
  preserving the existing compact fields selection.
- Updated connector tests around bearer-token propagation, Gmail pagination,
  Gmail metadata hydration, Drive pagination, and error handling.

Portfolio angle:

- Moves Gmail and Drive closer to real SaaS evidence ingestion instead of a
  first-page skeleton.
- Preserves the three-developer merge contract because provider pagination is
  hidden behind the same `GoogleConnector` and `SourceEvent` boundary.
- Keeps the cost story explicit: sync fetches only source metadata/content
  needed for review candidates and still does not trigger embeddings or LLM
  calls by itself.

Cost/security note:

- Gmail hydration uses `format=metadata` rather than full message bodies, which
  reduces payload size while keeping timeline author/title/date quality.
- Drive listing keeps a narrow fields projection and does not download file
  contents during connector sync.

Verification evidence:

- Added focused regression tests for paginated Gmail and Drive collection.
- `uv run pytest backend/tests/test_google_connector.py -v` passed with 7
  tests.
- `uv run pytest backend/tests/test_google_connector.py backend/tests/test_connector_factory.py backend/tests/test_google_oauth.py backend/tests/test_integration_runtime_status.py -v`
  passed with 26 tests.
- `uv run ruff check backend/app/connectors/google.py backend/tests/test_google_connector.py`
  passed.

## Slack Incremental Live Sync Cursor

What changed:

- Added a Slack live sync cursor path that derives the latest ingested
  `channel_id` + `ts` per channel from existing source metadata.
- `sync_connector_events` now passes that cursor to connectors that support
  incremental fetching, while older/mock connectors still use `fetch_events()`.
- `SlackConnector` forwards channel cursors to `SlackWebApiClient`, and the web
  client sends Slack `conversations.history` an `oldest` timestamp.
- Updated the Slack runbook with cursor behavior, test policy, and cost notes.

Portfolio angle:

- Shows ParaWorks moving from duplicate-skipping after collection to true
  source-delta collection before downstream work.
- Gives the Slack Agent track a safer merge contract: live Slack sync can evolve
  behind `fetch_events_since(...)` without forcing schema changes or frontend
  churn.
- Strengthens the AI-cost story because fewer repeated source events reach
  review generation, agent drafting, or later RAG indexing.

Cost/security note:

- The cursor lookup is local database metadata only. It does not call Slack,
  LLMs, or embedding providers.
- Slack message bodies still stay out of terminal logs; only channel/timestamp
  metadata is used to narrow the next API window.

Verification evidence:

- Added RED tests for Slack `oldest` handling and ingestion cursor passing,
  then implemented the minimal code until they passed.
- `uv run pytest backend/tests/test_slack_connector.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_connector_factory.py backend/tests/test_integration_runtime_status.py -v`
  passed with 24 tests.
- `uv run ruff check backend/app/connectors/slack.py backend/app/ingestion/sync.py backend/tests/test_slack_connector.py backend/tests/test_connector_ingestion_contract.py`
  passed.

## Slack Live Sync Retry Guardrails

What changed:

- Added bounded retry handling to `SlackWebApiClient` for Slack `429`
  rate-limit responses and transient `5xx` history API failures.
- Honored Slack `Retry-After` headers when present, with a safe default delay
  for transient errors that do not include the header.
- Converted exhausted retry paths into clear `SlackApiError` messages so sync
  endpoints can keep returning controlled failure states.
- Updated Slack runbook guidance and tests for retry behavior.

Portfolio angle:

- Makes the live Slack integration more production-like: API rate limits and
  temporary provider failures are expected operating conditions, not demo-only
  surprises.
- Strengthens the three-developer integration contract because Slack connector
  resilience stays behind the connector boundary and does not leak into agent
  or frontend code.

Cost/security note:

- Retries are intentionally bounded. ParaWorks can recover from transient Slack
  failures without creating unlimited provider calls or cascading into repeated
  review/LLM/embedding work.
- Retry handling does not log message bodies or expose bot tokens.

Verification evidence:

- Added RED tests for Slack rate-limit retry, retry exhaustion, and transient
  server-error recovery.
- Focused retry tests passed after implementation.
- `uv run pytest backend/tests/test_slack_connector.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_connector_factory.py backend/tests/test_integration_runtime_status.py -v`
  passed with 27 tests.
- `uv run ruff check backend/app/connectors/slack.py backend/tests/test_slack_connector.py`
  passed after Ruff applied import/format cleanup.

## LangGraph Evidence Cache Reuse

What changed:

- Added evidence cache planning to the Company Memory LangGraph orchestration
  path.
- The orchestration cost plan now builds Slack, Mail/Docs, and RAG evidence
  packets before execution, computes their evidence cache keys, and checks for
  completed matching `AgentRun` records.
- Unchanged evidence now produces `use_cache` decisions and avoids creating
  duplicate Slack/Mail review candidates or repeated RAG agent runs.
- Exposed `evidence_cache_reuse=true` in the orchestration cost policy API.

Portfolio angle:

- Shows a realistic multi-agent orchestration concern: merging multiple agent
  tracks safely means the orchestrator must decide when not to run agents.
- Strengthens the cost-optimization story because repeated user clicks over
  unchanged Slack/Gmail/Drive/RAG evidence no longer create duplicate agent
  spend or noisy review work.
- Keeps the split between three developers clean: each agent owns its packet
  and cache key contract, while LangGraph owns the run/skip/cache decision.

Cost/security note:

- Cache planning is local database lookup plus deterministic evidence hashing.
  It does not call Slack, Google, embeddings, or paid LLM APIs.
- Cached decisions still preserve the explicit POST execution boundary; status
  and dry-run endpoints remain zero-cost.

Verification evidence:

- Added a RED test proving a second identical Company Memory run should use
  cache and create no new `AgentRun`/`ReviewItem` records.
- Added a RED API test for `evidence_cache_reuse` in orchestration cost policy.
- `uv run pytest backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py backend/tests/test_agent_runs_api.py -v`
  passed with 11 tests.
- `uv run pytest backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py -v`
  passed with 7 tests after Ruff cleanup.
- `uv run ruff check backend/app/agent_runtime/company_memory.py backend/app/api/v1/orchestration.py backend/app/agents/slack_agent/__init__.py backend/app/agents/rag_orchestrator_agent/__init__.py backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py`
  passed.

## Admin Audit Log Foundation

What changed:

- Added an `AuditLog` model and admin-only `/api/v1/admin/audit-logs` API.
- Recorded audit events for review approval, bulk agent-candidate approval,
  review reject/more-evidence actions, connector sync, agent review runs,
  Company Memory LangGraph runs, and RAG reindex execution/job creation.
- Added sanitized audit metadata so operational context is visible without
  exposing tokens or secret references.
- Extended `/admin` with a recent audit log panel using the same Liquid Glass
  card system as the rest of the workspace.

Portfolio angle:

- Shows service maturity beyond feature demos: important operational actions
  are now attributable to an actor, target, timestamp, and metadata.
- Strengthens the three-developer workflow because merged AI-generated work can
  be reviewed through a shared audit trail instead of scattered terminal logs.
- Makes permission design more concrete: employees cannot read audit logs,
  while admins can inspect workspace activity from the product UI.

Cost/security note:

- Audit writes are local database operations. They do not call Slack, Google,
  embeddings, or LLM APIs.
- Audit metadata is sanitized before persistence so token-like strings are not
  rendered in the admin console.

Verification evidence:

- Added RED tests first for missing `AuditLog` model/API and key action audit
  records.
- `uv run pytest backend/tests/test_audit_logs.py backend/tests/test_auth_api.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_orchestration_api.py backend/tests/test_integration_runtime_status.py -v`
  passed with 23 tests.
- `uv run pytest backend/tests/test_audit_logs.py -v` passed with 6 tests after
  Ruff cleanup.
- `uv run ruff check backend/app/models/audit.py backend/app/services/audit.py backend/app/api/v1/admin.py backend/app/api/v1/router.py backend/app/api/v1/review.py backend/app/api/v1/integrations.py backend/app/api/v1/orchestration.py backend/app/api/v1/rag.py backend/tests/test_audit_logs.py`
  passed.
- `npx eslint src/app/admin/page.tsx src/lib/api/types.ts` passed.
- `npm run build` passed and included `/admin`.

## RAG Ranked Citation Quality

What changed:

- Reworked keyword retrieval from exact full-query substring matching to
  term-based candidate scoring.
- Search and Ask responses now include ranked citations with source id, source
  URL, source type, permission level, snippet, relevance score, and matched
  query terms.
- Ask keeps restricted evidence hidden while still reporting hidden match
  counts and returning only visible citations to the current user.
- Updated the Company Memory search UI to show citation scores and matched
  terms beside answer/search evidence.

Portfolio angle:

- Makes the RAG layer explainable: users can see why evidence appeared, not
  only that an answer was generated.
- Demonstrates permission-aware retrieval quality, including visible citation
  filtering and hidden-match disclosure.
- Strengthens the final product story because Slack/Gmail/Drive/approved
  knowledge can now flow into answerable, cited company memory.

Cost/security note:

- Ranking and citation generation are deterministic local scoring operations.
  They do not call embedding providers or paid LLMs.
- Permission checks still run before citations are returned, so restricted
  source URLs/snippets are not exposed to employee viewers.

Verification evidence:

- Added RED tests for ranked search citations and Ask citations with hidden
  restricted matches.
- `uv run pytest backend/tests/test_rag_quality.py backend/tests/test_search_permissions.py backend/tests/test_ask_api.py backend/tests/test_rag_orchestrator_service.py backend/tests/test_vector_retriever.py -v`
  passed with 16 tests.
- `uv run ruff check backend/app/api/v1/search.py backend/app/api/v1/ask.py backend/app/agents/rag_orchestrator_agent/agent.py backend/app/agents/rag_orchestrator_agent/service.py backend/tests/test_rag_quality.py`
  passed.
- `npx eslint src/app/search/page.tsx src/lib/api/types.ts` passed.
- `npm run build` passed and included `/search`.

## Google Live Delta And Retry Guardrails

What changed:

- Added Gmail and Google Drive incremental cursor support to the live Google
  connector.
- Gmail collection now sends an `after:<unix_seconds>` query from the last
  stored message `internalDate`.
- Drive collection now sends a `modifiedTime > '<timestamp>'` query from the
  last stored file modification time.
- Google source events now persist common `sync_partition` and `sync_cursor`
  metadata so ingestion can resume without connector-specific database logic.
- Added bounded retry handling for Google API 429 and 5xx responses, including
  `Retry-After` support.

Portfolio angle:

- Shows the project is moving from demo integration buttons toward production
  ingestion behavior: delta fetch, retry, and observable failure boundaries.
- Makes the Google track easier for another developer to own because the
  ingestion cursor contract is shared with Slack rather than hidden in one
  connector.

Cost/security note:

- The connector fetches only source deltas before review, agent execution, or
  embedding work. This prevents every sync from reprocessing unchanged Gmail
  and Drive content.
- Retry is bounded, so rate limit or server-side failures do not create runaway
  API usage.

## Whole-App Playwright Regression Matrix

What changed:

- Added a route inventory guard that fails when a new `app/**/page.tsx` route is
  not represented in Playwright coverage.
- Added a whole-page regression matrix for desktop and mobile, dark and light
  modes, including `/`, static pages, OAuth callback pages, and the dynamic
  agent run detail page.
- The matrix checks that each page mounts the workspace shell, avoids Next error
  screens, has visible glass surfaces, stays nonblank, and does not introduce
  horizontal viewport overflow.
- Added an AppShell hydration marker so interaction tests wait for real React
  handlers before clicking theme toggles or submitting global search.
- Hardened existing smoke tests around hydration, route interception, and admin
  audit-log text duplication.
- Fixed Search page compatibility with older Ask responses that do not include
  `citations`, and removed duplicate React keys in search evidence rendering.

Portfolio angle:

- Turns browser QA from manual spot checks into repeatable desktop/mobile
  coverage for every current Next.js page.
- Demonstrates integration discipline: new routes must be added to the
  regression inventory instead of silently escaping visual smoke coverage.

Cost/security note:

- The new page regression matrix validates UI and local route health only; it
  does not trigger paid LLM or embedding calls.
- Existing cost-related smoke tests still mock dry-run and approval responses
  so CI-style browser checks remain deterministic.

## Google Source Quality And Calendar Delta Sync

What changed:

- Gmail live collection now hydrates messages with `format=full` and extracts
  bounded `text/plain` payload content for review/RAG instead of relying only on
  snippets.
- Gmail source metadata now records thread id, labels, date header, body source,
  and whether the extracted body was truncated for ingestion safety.
- Google Drive source events now include description, owner, last modifier,
  created time, modified time, and richer searchable body text.
- Google Calendar live collection now paginates events and supports `updatedMin`
  incremental sync through the shared `sync_partition` / `sync_cursor` contract.
- Calendar source events now include description, location, start/end time,
  attendee count, and reusable sync cursor metadata.

Portfolio angle:

- Moves Google integrations beyond "connected" status into useful business
  memory ingestion: mail context, document metadata, and calendar timelines now
  carry enough structure for review and RAG.
- Shows cross-connector consistency because Gmail, Drive, and Calendar all share
  the same incremental cursor pattern.

Cost/security note:

- Gmail body extraction is bounded before review and embedding stages, reducing
  the risk of large messages driving unnecessary downstream token cost.
- Calendar sync uses `updatedMin` so repeated syncs avoid full event history
  collection.

## Source Evidence Review Drawer

What changed:

- Review Queue responses now include structured `source_evidence` rows with
  source URL, snippet, permission level, confidence score, rank, importance
  score, source id, author/timestamp when available, and originating AgentRun.
- The Review UI drawer now presents source evidence as reviewer-ready cards
  instead of only raw links and snippets.
- The "request more evidence" workflow now captures a reviewer note and stores
  it in the ReviewItem payload before moving the item to
  `needs_more_evidence`.

Portfolio angle:

- Makes the human-in-the-loop trust boundary more concrete: reviewers can see
  exactly what evidence supports an AI-generated timeline, history, decision,
  or todo candidate.
- Shows practical product ownership for Track C because orchestration output is
  now reviewable by Korean business users, not only visible in backend logs.

Cost/security note:

- Structured evidence is assembled from already persisted ReviewItem and
  AgentRun metadata. It does not call Slack, Google, embeddings, or paid LLMs.
- The Drawer preserves permission labels and source snippets so reviewers can
  reject or request more evidence before any candidate becomes trusted
  knowledge.

## LangGraph HITL Checkpoint Strategy

What changed:

- Company Memory orchestration now emits a structured `hitl_checkpoint` output
  from the `draft_review_candidates` node.
- The checkpoint records the Review Queue as the current HITL store, the target
  ReviewItem ids, required statuses, resume node, resume policy, and whether
  trusted knowledge requires human approval.
- The orchestration status cost policy now explicitly reports
  `hitl_checkpointing`, `checkpoint_store=review_queue`, and
  `trusted_knowledge_requires_approval`.

Portfolio angle:

- Shows that ParaWorks' LangGraph flow is not a black-box automation pipeline:
  it has an explicit human review stop before generated memory becomes trusted
  organizational knowledge.
- Gives the three-developer team a stable integration contract for future
  long-running checkpoint/resume work without changing each agent's local
  implementation.

Cost/security note:

- HITL checkpoint metadata is generated from local ReviewItem ids and
  orchestration state. It does not call paid LLMs, embeddings, Slack, or Google.
- The checkpoint keeps the trust boundary visible: generated outputs can be
  reviewed, rejected, or marked as needing more evidence before promotion.

## Quality And Permission Regression Suite

What changed:

- Added a focused backend regression suite for ParaWorks' core trust promises.
- The suite verifies that source-less Review Queue items cannot be approved.
- It verifies that employee/viewer RAG responses report hidden restricted
  matches without leaking restricted snippets or citations.
- It verifies that Company Memory orchestration emits a Review Queue HITL
  checkpoint without triggering paid calls.
- It verifies that cache-hit orchestration runs do not duplicate AgentRun or
  ReviewItem records.

Portfolio angle:

- Converts product principles into executable tests: evidence-first, permission
  safe, cost-aware, and human-reviewed.
- Gives the three-developer team a shared safety net before connector quality
  and structured LangChain outputs become more complex.

Cost/security note:

- The regression suite uses deterministic local fixtures and fake harness
  models. It does not call live Slack, Google, OpenAI, Gemini, embeddings, or
  external APIs.
- The tests make cost control observable by asserting cache reuse and no
  duplicate review/agent records on unchanged evidence.

## Cross-Agent Evidence Summary Metadata

What changed:

- Added a shared `build_evidence_summary` helper for turning `EvidencePacket`
  messages into AgentRun evidence summary rows.
- Mail/Document Agent runs now persist source id, URL, source type, timestamp,
  author, permission, rank, importance score, and snippet metadata.
- Track C Timeline/History/Decision/Todo extraction runs now persist the same
  evidence summary metadata, so Review Drawer rows can become richer beyond
  Slack-only candidates.

Portfolio angle:

- Strengthens the three-track architecture because Drawer evidence is no
  longer a Slack-specific affordance; Mail/Docs and orchestration-owned memory
  agents now expose the same review/debug metadata.
- Makes future LangChain structured-output replacement safer because the
  Review UI depends on shared EvidencePacket-derived metadata rather than each
  agent inventing local evidence shapes.

Cost/security note:

- Evidence summaries are derived from already-selected evidence packets and
  stored with AgentRun metadata. They do not trigger extra provider calls.
- Permission labels remain attached to each evidence row for reviewer and RAG
  safety checks.

## Search Retrieval Backend Alignment

What changed:

- Verified that `/search` page calls both `/api/v1/ask` and `/api/v1/search`.
- Before this update, `/api/v1/ask` could use pgvector behind the feature flag,
  while `/api/v1/search` always used deterministic lexical ranking.
- Added a shared pgvector search adapter builder and wired `/api/v1/search` to
  use the same pgvector feature-flag path when PostgreSQL, pgvector search flag,
  and an OpenAI embedding key are available.
- Search responses now disclose `retrieval_backend` and cost policy metadata,
  and the `/search` UI shows whether the current result used pgvector or the
  zero-cost deterministic search path.

Portfolio angle:

- Makes RAG behavior explainable to users and interviewers: answer generation
  and evidence search now report which retrieval path they used.
- Shows cost-aware product design because query-time embedding calls are
  explicit instead of hidden behind a generic search button.

Cost/security note:

- Default SQLite/demo mode remains `deterministic_lexical` with no embedding or
  paid LLM call.
- pgvector search performs a query embedding only when
  `RAG_USE_PGVECTOR_SEARCH=true`, PostgreSQL is active, and `OPENAI_API_KEY` is
  configured.
- Permission filtering and hidden-match accounting remain enforced in both
  retrieval paths.

## Slack Thread Context-Aware Chunking

What changed:

- Slack thread replies now preserve parent-message context in the SourceEvent
  body before ingestion creates the document chunk.
- Reply metadata now records `thread_parent_text`, `thread_reply_index`, and
  `thread_context_window=parent_plus_reply`.
- The connector still fetches thread replies incrementally from the channel
  cursor, so this quality improvement does not require re-fetching entire
  channel history by default.

Portfolio angle:

- Improves evidence quality for real collaboration data: short replies such as
  "동의합니다" or "좋아요" become useful to agents/RAG because the parent
  decision context travels with the reply chunk.
- Strengthens Track A ownership by making Slack ingestion more agent-ready,
  not just API-connected.

Cost/security note:

- This is deterministic preprocessing over already fetched Slack events. It
  does not call Slack more than the existing reply fetch, and it does not call
  LLMs or embeddings.
- Parent context is bounded to one parent message plus one reply, avoiding
  whole-thread prompt inflation.

## Gmail Thread And Domain Metadata Quality

What changed:

- Gmail SourceEvents now parse participants from From, To, and Cc headers.
- Gmail metadata now records `thread_context_key`, `from_domain`,
  `participant_domains`, `external_domains`, and
  `has_external_participants`.
- Existing body extraction, truncation, label ids, thread id, and delta cursor
  behavior remain intact.

Portfolio angle:

- Makes Gmail evidence more useful for business review: agents can distinguish
  internal-only messages from customer/vendor-involved threads.
- Supports future permission and routing policies without hard-coding Gmail
  parsing logic inside agent implementations.

Cost/security note:

- This is local header parsing over already fetched Gmail message payloads.
  It does not add Google API calls, LLM calls, or embedding calls.
- Domain metadata enables safer future filtering while keeping raw content
  behind the existing Review/RAG permission checks.

## Drive Parser Status And Version Metadata

What changed:

- Google Drive SourceEvents now preserve `parser_name`, `parser_status`,
  `parser_status_reason`, `document_version`, `revision_id`, and
  `content_signature`.
- Drive API collection now requests `version` and `headRevisionId` so future
  parser/indexing work can decide whether content actually changed.
- The current parser status is explicit as `metadata_only`, matching the
  harness stage before full file export/parsing is enabled.

Portfolio angle:

- Shows product-quality ingestion design: document evidence carries parser and
  version provenance instead of appearing as anonymous text.
- Supports later incremental parsing, embedding skip decisions, and reviewer
  trust signals without changing agent contracts.

Cost/security note:

- This adds metadata fields to the existing Drive files list request; it does
  not export document bodies, call LLMs, or call embedding APIs.
- `content_signature` gives the future indexer a cheap guardrail for skipping
  unchanged Drive files before paid embedding work.

## Calendar Event Quality Metadata

What changed:

- Calendar SourceEvents now preserve `event_context_key`, `event_status`,
  organizer/creator emails, `recurring_event_id`, attendee response counts,
  attendee domains, external domains, and event duration.
- Participants still come from attendee emails, but metadata now explains who
  accepted, declined, or has not responded.
- The connector keeps the same delta sync boundary through the event `updated`
  cursor.

Portfolio angle:

- Makes calendar evidence more useful for Korean business review flows:
  meetings can be understood as internal/external, confirmed/cancelled, and
  time-bounded evidence.
- Gives future Timeline/History agents better deterministic signals before
  spending LLM tokens.

Cost/security note:

- This is local metadata derivation from already fetched Calendar event
  payloads. It adds no Google calls, LLM calls, or embedding calls.
- External-domain flags support safer future permission and disclosure
  policies without leaking hidden event content.

## Connector Golden Dataset Fixtures

What changed:

- Added `backend/tests/fixtures/connector_golden_payloads.json` covering
  Slack, Gmail, Drive, and Calendar payloads.
- Added a regression test that asserts each connector preserves agent-ready
  metadata: Slack thread context, Gmail external domains, Drive parser/version
  metadata, and Calendar RSVP/duration/external-domain metadata.
- The fixture is intentionally deterministic and local, so it can run in every
  developer and coding-assistant workflow.

Portfolio angle:

- Demonstrates team-scale AI-assisted development discipline: connector quality
  is measured by stable examples, not only by manual UI inspection.
- Gives three developer tracks a shared contract for evidence metadata before
  they build more source-specific agents and RAG evaluation.

Cost/security note:

- Golden tests use static local payloads and make no Slack, Google, LLM, or
  embedding calls.
- The fixture protects future cost optimizations such as hash/signature skips
  by keeping metadata expectations explicit.

## RAG Precision Recall Smoke Metrics

What changed:

- Added `backend/app/rag/evaluation.py` with deterministic retrieval metrics:
  precision@k, recall@k, hit rate, expected/retrieved counts, and matched
  expected source ids.
- Added `backend/tests/fixtures/rag_smoke_eval_cases.json` and a smoke test
  that seeds known chunks, runs deterministic retrieval, and verifies the
  expected sources are recovered.
- The test complements `/search` backend disclosure by measuring whether the
  zero-cost retrieval path still finds the right evidence.

Portfolio angle:

- Shows evaluation-minded RAG engineering: retrieval quality is tracked with a
  repeatable smoke metric before adding more expensive model-based evaluation.
- Gives interview/demo material for explaining why ParaWorks avoids blind LLM
  calls and validates evidence selection first.

Cost/security note:

- The smoke metric uses local fixtures and deterministic retrieval only.
  It makes no paid LLM, embedding, Slack, or Google calls.
- This is the correct first guardrail before enabling broader pgvector or
  model-judge evaluation.

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
- `feat: add langgraph orchestration foundation`
- `feat: expose langgraph orchestration api`
- `feat: show langgraph orchestration status`
- `feat: add langgraph dry-run operations ux`
- `feat: run agents through langgraph`
- `feat: bulk approve agent candidates`
- `feat: show slack runtime status`
- `feat: show google runtime status`
- `feat: add execution cost plan`
- `fix: redact runtime status secrets`
- `docs: add portfolio case study`
- `test: harden integration sync smoke selector`
- `feat: add liquid glass frontend theme`
- `feat: intensify liquid glass theme`
- `feat: add dark liquid glass mode`
- `style: tune dark glass gray purple palette`
- `style: refine dark glass consistency`
- `style: unify integration runtime glass`
- `style: tokenize shell theme chrome`
- `style: tune light gray purple palette`
- `style: soften light purple palette`
- `feat: add agent cost budget guardrails`
- `feat: expose agent budget observability`
- `feat: activate global search bars`
- `feat: activate google oauth callback`
- `style: tune light deep purple palette`
- `feat: add demo login and admin console`
- `style: unify workspace glass cards`
- `chore: harden pgvector dev path`
- `feat: gate paid embedding reindex cost`
- `feat: add rag reindex approval ux`
- `feat: harden google live collection`
- `feat: add slack incremental sync cursor`
- `feat: add slack live sync retry guardrails`
- `feat: reuse cached langgraph evidence`
- `feat: add admin audit logs`
- `feat: improve rag citation ranking`
- `feat: harden google live sync deltas`
- `test: expand whole-app playwright regression`
- `feat: enrich google live source quality`
- `feat: strengthen slack live agent handoff`
  - Slack sync can now receive selected channel IDs from the integrations UI while keeping `.env` channel IDs as the default safe fallback.
  - Slack live collection now follows thread replies incrementally from the same channel cursor, avoiding full-thread re-vectorization/reprocessing on every sync.
  - Slack runtime status exposes channel options, latest sync counts, actionable Slack error hints, and whether synced Slack sources are ready for agent testing.
  - Verification: backend suite `185 passed, 1 skipped`; frontend lint/build passed; Playwright integrations desktop dark/light regression passed.
- `test: validate slack live sync path`
  - Switched local smoke mode to live, restarted backend/frontend, and verified backend health reported `demo_mode=False`.
  - Executed Slack live sync for the configured selected channel; Slack API path completed successfully with no new delta events.
  - Ran Slack Agent review on existing synced Slack sources; one review candidate was created and runtime status reported agent testing readiness.
  - Verification: Playwright integrations desktop dark/light regression passed in live mode.
- `feat: add slack real llm adapter guardrails`
  - Added a LangChain-based Slack Agent adapter with OpenAI as the primary provider and Gemini as a fallback provider chain.
  - Added paid-run preflight that reports provider availability, estimated tokens, estimated cost, budget status, and requires explicit confirmation before live LLM calls.
  - Kept the deterministic Slack Agent as the default safe harness while exposing a separate real LLM test action in the integrations UI.
  - Verification: backend suite `191 passed, 1 skipped` with demo-mode override; frontend lint/build passed; Playwright integrations desktop dark/light regression passed.
- `fix: make slack llm preflight conservative`
  - Ran one confirmed real Slack LLM test with OpenAI primary and Gemini fallback configured; it created one review candidate and persisted an AgentRun.
  - Found the first preflight underestimated Korean/Slack JSON token usage, then tightened prompt caps and changed input-token estimation to a conservative character-count floor.
  - After the fix, the same live Slack evidence window is blocked as `over_budget` instead of allowing another paid run under an optimistic estimate.
  - Verification: backend suite `193 passed, 1 skipped` with demo-mode override; frontend lint passed; Playwright integrations desktop dark/light regression passed.
- `feat: bound slack llm evidence window`
  - Limited paid Slack LLM runs to a recent evidence window instead of sending every synced Slack message to the model.
  - Added shared windowing for preflight and paid execution so the estimated input and actual prompt use the same bounded packet.
  - Added UI visibility for evidence message count and kept the conservative budget cap, enabling a live run over 12 recent Slack messages within the configured budget.
  - Verification: backend suite `195 passed, 1 skipped` with demo-mode override; frontend lint/build passed; Playwright integrations desktop dark/light regression passed.
- `feat: rank slack llm evidence`
  - Replaced the temporary recent-only paid Slack LLM window with deduped, importance-ranked evidence selection while keeping full Slack sync unchanged.
  - Ranking now prioritizes decision, action, cost, technical, thread, and recency signals; duplicate message bodies collapse before top-k selection.
  - Preflight and paid execution use the same ranked source window, and prompt rendering dynamically shrinks evidence text to stay inside the configured per-run cost budget.
  - Verification: backend suite `197 passed, 1 skipped`; frontend build passed; Playwright integrations desktop dark/light regression passed; live preflight returned `slack:live:ranked:12` at `$0.000966 / $0.001`.
- `feat: expose ranked evidence in orchestration`
  - Ran a confirmed live ranked Slack LLM test; the persisted AgentRun used `slack:live:ranked:12` and actual usage was 2,525 tokens at about `$0.000435`.
  - AgentRun records now store a compact ranked evidence summary, and the detail API/UI promote rank, score, source, permission, and snippet for review/debugging.
  - LangGraph company-memory orchestration now uses the same ranked Slack evidence window and exposes source window, selection strategy, evidence count, and cost plan metadata.
  - Verification: backend suite `199 passed, 1 skipped`; frontend build passed; AgentRun desktop/mobile Playwright regression passed; local orchestration API returned `orchestrated-slack:ranked:12` at `$0.000104 / $0.001`.
- `feat: add track c extraction boundaries`
  - Added deterministic Track C agents for Timeline, History, Decision Record, and Todo extraction plus a Validation gate before Review Queue persistence.
  - Extended `ReviewCandidate` with structured payload fields so each candidate can preserve type-specific fields such as `decision_summary`, `result_summary`, `reason`, `priority`, and `priority_reason`.
  - LangGraph company-memory orchestration now runs Track C extraction after source-specific agents create fresh review candidates, while cache-hit runs avoid duplicate candidate generation.
  - Verification: backend suite `203 passed, 1 skipped`; Ruff passed; local orchestration API returned cache-safe `memory_review_items_created=0` when source agents reused cached evidence.
- `feat: add review source evidence drawer`
  - Review Queue API exposes structured source evidence and originating AgentRun metadata for Drawer rendering.
  - Reviewers can request more evidence with a note, preserving why the candidate was not ready for approval.
- `feat: add orchestration hitl checkpoint policy`
  - Company Memory orchestration now emits Review Queue checkpoint metadata with resume policy and required review statuses.
  - Orchestration status APIs expose HITL checkpointing as part of the cost/trust policy.
- `test: add quality permission regression suite`
  - Added focused guardrails for evidence-first approval, restricted RAG hiding, HITL checkpoint metadata, and cache dedupe.
- `feat: add cross-agent evidence summaries`
  - Mail/Docs and Track C memory extraction AgentRuns now persist source evidence summary metadata for richer Review Drawer inspection.
- `feat: align search retrieval backend`
  - `/api/v1/search` now reports its retrieval backend and can use the same pgvector feature-flag path as `/api/v1/ask`.
- `feat: add slack thread context chunks`
  - Slack reply chunks now include parent message context and thread metadata for better Review/RAG evidence quality.
- `feat: enrich gmail thread domain metadata`
  - Gmail events now preserve thread context keys, participants, participant domains, and external-domain flags.
- `feat: add drive parser version metadata`
  - Drive events now preserve parser status, document version, revision id, and content signatures for safer parsing/indexing.
- `feat: add calendar event quality metadata`
  - Calendar events now preserve event context, status, organizer, RSVP counts, duration, and external attendee domains.
- `test: add connector golden dataset`
  - Added static Slack/Gmail/Drive/Calendar golden payloads and metadata regression assertions.
- `test: add rag retrieval smoke metrics`
  - Added local precision/recall/hit-rate evaluation for deterministic RAG retrieval fixtures.
