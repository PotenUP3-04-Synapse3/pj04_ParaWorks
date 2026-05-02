# ParaWorks Product Plan

## 1. Direction

ParaWorks is a Korean-first, multi-agent company memory product.

The original merged plan remains a reference architecture, but this file is the
current execution plan. The product is being built by three developers, so the
implementation must optimize for clear ownership, stable contracts, frequent
integration, and portfolio-quality evidence of collaboration.

The product goal is not a generic project-management tool. ParaWorks should help
business users ask:

- What happened?
- Why did we decide that?
- Which evidence supports this timeline, history, decision, or todo?
- What changed across Slack, email, documents, and company knowledge?
- Can this answer be trusted under the current user's permissions?

Every AI result must preserve source links, snippets, confidence, permission
level, cost metadata, and human-review status.

## 2. Product Principles

1. Evidence first
   - No source evidence means no Review Queue item.
   - LLM output starts as `pending_review`, never as trusted knowledge.

2. Korean business user first
   - UI copy, review flows, and summaries should be comfortable for Korean
     business users.
   - English can remain for developer/debug labels when it improves clarity.

3. Cost-aware by default
   - Do not send full synced corpora to paid LLMs.
   - Use delta sync, content hashes, dedupe, ranked evidence windows, cache
     reuse, token caps, and explicit paid-run confirmation.
   - Cost savings should be visible in API responses, UI, logs, and portfolio
     notes.

4. Permission-safe by default
   - Source permissions and ParaWorks RBAC both matter.
   - Restricted input cannot produce broader output.
   - Retrieval must report hidden matches without leaking content.

5. Team-scale architecture
   - Each developer owns a product agent/domain, not just a technical layer.
   - Shared contracts live in `backend/app/agent_runtime/`.
   - Agent implementations communicate through contracts, Review Queue, and
     LangGraph, not direct cross-agent imports.

## 3. Three Developer Tracks

### Track A. Communication Intelligence

Primary owner: Developer A

Scope:

- Slack integration and Slack Agent
- Gmail integration handoff with Track B where needed
- Slack/Gmail message and thread evidence extraction
- conversation summarization
- ranked evidence selection
- timeline/history/todo candidate creation from communication sources
- source URL and thread context preservation

Current state:

- Slack OAuth and live sync boundary exist.
- Slack selected-channel sync and incremental cursor logic exist.
- Real Slack LLM adapter exists with OpenAI primary and Gemini fallback.
- Paid LLM runs use ranked, deduped, budget-capped evidence windows.
- Slack AgentRun detail exposes ranked evidence summary.

Next priorities:

1. Improve Slack thread context-aware chunking.
2. Add Gmail thread collection quality checks.
3. Expand communication-specific extraction prompts/schemas.
4. Add communication golden dataset cases.

### Track B. Document and Knowledge Pipeline

Primary owner: Developer B

Scope:

- Google Drive integration
- internal document ingestion
- document parsing and chunking
- Gmail document/attachment boundary where relevant
- pgvector indexing
- approved knowledge indexing
- Knowledge Asset pipeline
- source/version metadata quality

Current state:

- Google OAuth and installed sync boundary exist.
- Gmail/Drive source collection path exists in harness form.
- pgvector adapter and incremental vector indexing exist.
- RAG indexing observability and reindex approval UX exist.
- Embedding calls are guarded by delta/hash skip logic.

Next priorities:

1. Harden Google Drive file parsing by type.
2. Add parser run records and parse status.
3. Improve document metadata: document version, parser name, page/paragraph.
4. Prepare HWP/HWPX parser adapter decision.
5. Add document golden dataset cases.

### Track C. Orchestration and Review Product

Primary owner: Developer C

Scope:

- LangGraph orchestration
- Review Queue and human-in-the-loop
- RAG answer agent
- DecisionRecord, Timeline, History, Todo, Validation boundaries
- permission-aware answer generation
- token-cost routing, caching, model policy
- frontend review/search/agent observability

Current state:

- LangGraph company-memory workflow exists.
- Slack, Mail/Docs, and RAG agent runs are orchestrated.
- Review Queue approval promotes reviewed candidates into knowledge tables.
- AgentRun cost summary and detail views exist.
- Ranked Slack evidence is visible in orchestration and AgentRun detail.

Next priorities:

1. Split candidate extraction into explicit Timeline, History, Decision, Todo,
   and Validation boundaries under Track C.
2. Add Source Evidence Drawer and "request more evidence" UX.
3. Add LangGraph HITL checkpoint strategy.
4. Add quality and permission regression suite.

## 4. Shared Runtime Contracts

Shared contracts are the team integration layer.

Current shared concepts:

- `EvidencePacket`
- `EvidenceMessage`
- `ReviewCandidate`
- `PermissionContext`
- `AgentRunResult`
- `AgentRunCost`
- `AgentManifest`
- `AgentRegistry`

Rules:

- Contract changes require tests before implementation.
- Contract changes must update all affected tracks.
- Agents must preserve source links, snippets, confidence, permission level, and
  uncertainty reason.
- Review Queue is the trust boundary.

Near-term contract improvements:

1. Add structured candidate payload fields for:
   - `timeline_event`
   - `history_event`
   - `decision_record`
   - `todo`
2. Add validation result metadata:
   - `validation_status`
   - `missing_evidence`
   - `faithfulness_status`
   - `permission_status`
3. Add source evidence summaries for UI display.

## 5. Architecture

```text
Next.js app
  -> FastAPI API
  -> connector ingestion
  -> Source / Document / DocumentChunk
  -> pgvector / deterministic smoke retrieval
  -> LangGraph orchestration
  -> source-specific agents
  -> Review Queue
  -> approved knowledge tables
  -> RAG answer/search surfaces
```

Default production direction:

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- DB: PostgreSQL + pgvector
- Queue: Celery + Redis
- Frontend: Next.js App Router, TypeScript, Tailwind
- Agent: LangChain >= 1.2 and current LangGraph
- Human review: Review Queue first, LangGraph checkpoint later

SQLite smoke mode must continue working for local demo and tests.

## 6. MVP Definition

MVP is complete when ParaWorks can:

1. Connect or simulate Slack, Gmail, Google Drive, and Google Calendar sources.
2. Store source evidence with permission metadata.
3. Parse/chunk evidence into searchable records.
4. Index approved and source evidence into pgvector when enabled.
5. Run source agents through LangGraph.
6. Create pending Review Queue candidates for:
   - Timeline
   - History
   - Decision Record
   - Todo
7. Show source evidence and confidence to reviewers.
8. Approve/reject/request-more-evidence.
9. Promote approved items into trusted knowledge tables.
10. Answer user questions with permission-aware RAG.
11. Show AgentRun cost, token usage, cache, ranked evidence, and source window.
12. Pass whole-app Playwright smoke checks on desktop and mobile.

## 7. Current Completed Work

Completed harness slices include:

- Next.js frontend shell with Korean/English language option
- Slack-like workspace UI and messenger page
- Liquid Glass frontend theme iteration
- demo login and admin console
- Slack OAuth and runtime status
- Google OAuth and runtime status
- Slack live sync and incremental cursor
- Gmail/Drive installed sync boundary
- Review Queue approval and knowledge promotion
- pgvector adapter and incremental vector indexing
- RAG ask/search path with citation ranking
- LangGraph company-memory foundation
- agent cost budget observability
- OpenAI primary and Gemini fallback for Slack LLM runs
- ranked Slack LLM evidence selection with dedupe and cost caps
- AgentRun ranked evidence detail UI
- portfolio log and case-study documentation

## 8. Recommended Roadmap From Here

### Milestone 1. Track Alignment Documentation

Goal: Make the 3-track plan the source of truth.

Tasks:

- Keep this `plan.md` updated.
- Keep `AGENTS.md` aligned with this plan.
- Keep `docs/portfolio-log.md` updated after each milestone.
- Record integration rules for coding assistants.

### Milestone 2. Track C Extraction Boundaries

Goal: Make the original Phase 4 agents real, but owned under the orchestration
track.

Tasks:

- Add deterministic Timeline extraction boundary.
- Add deterministic History extraction boundary.
- Add deterministic Decision Record extraction boundary.
- Add deterministic Todo extraction boundary.
- Add Validation gate before Review Queue persistence.
- Wire them into LangGraph after source-specific agents.

Why next:

- It directly supports the product goal.
- It is portfolio-visible.
- It creates stable integration targets for Tracks A and B.

### Milestone 3. Source Evidence Drawer and Review UX

Goal: Make human review genuinely usable.

Tasks:

- Add Source Evidence Drawer.
- Show source URL, snippet, permission, rank, confidence, and agent run.
- Improve `needs_more_evidence` workflow.
- Add reviewer notes.

### Milestone 4. Connector Quality Hardening

Goal: Improve real data quality before adding more shiny features.

Tasks:

- Slack thread context-aware chunking.
- Gmail thread metadata and domain filtering.
- Drive file parser status and version metadata.
- Calendar ingestion boundary.

### Milestone 5. Evaluation and Regression Suite

Goal: Make quality measurable.

Tasks:

- Golden dataset for Slack, Gmail, Drive, Calendar.
- Permission leakage tests.
- Source validation tests.
- RAG precision/recall smoke metrics.
- Cost regression tests.

### Milestone 6. Product Completion Layer

Goal: Move from harness to product-like MVP.

Tasks:

- Projects and Decisions pages.
- Timeline and History views.
- Notifications.
- Knowledge Map, if time allows.
- Production auth plan: httpOnly cookie + refresh token.
- Deployment runbook.

## 9. Cost Policy

Every new agent or connector must answer:

- Does it avoid duplicate sync?
- Does it avoid duplicate embeddings?
- Does it bound paid LLM input?
- Does it reuse cache when evidence is unchanged?
- Does it expose estimated and actual token usage?
- Does it fail closed when over budget?

Default cost rules:

- Status APIs must not trigger paid LLM calls.
- Live paid LLM calls require explicit user action.
- Preflight and actual run must use the same evidence packet.
- Ranked/deduped evidence windows are preferred over recent-only windows.
- Full source sync is allowed; full source LLM input is not.

## 10. Quality Gates

Before a milestone is considered done:

- Backend tests pass.
- Frontend lint/build pass when frontend changed.
- Playwright checks run for affected pages.
- API smoke check runs for affected backend flows.
- `docs/portfolio-log.md` is updated.
- Changes are committed.

For live provider calls:

- Never print secrets.
- Run preflight first.
- Keep paid runs minimal and intentional.
- Record estimated vs actual cost when available.

## 11. How Coding Assistants Should Work

Coding assistants must:

1. Read this `plan.md` before major work.
2. Read `AGENTS.md`.
3. Check `git status --short`.
4. Identify which track owns the change.
5. Avoid cross-track rewrites unless the task is explicitly integration work.
6. Use tests before behavior changes.
7. Preserve cost and permission guardrails.
8. Update portfolio or handoff docs after meaningful milestones.

If the old merged plan and this file conflict, follow this file unless the user
explicitly says to return to the old plan.

