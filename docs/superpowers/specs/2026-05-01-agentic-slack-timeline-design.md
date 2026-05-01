# Agentic Slack Timeline Design

Date: 2026-05-01
Project: ParaWorks

## Purpose

This spec defines the first real AI-agent vertical slice for ParaWorks:

Slack channel and message ingestion -> LLM-assisted summary and review ->
timeline/history candidates -> Review Queue -> future RAG-ready knowledge.

The product goal is not "Slack clone with AI." ParaWorks should become a
Korean-first company knowledge operating system where multi-agent workflows
convert fragmented communication, email, and internal documents into reviewed,
permission-aware organizational memory.

## Final Product North Star

ParaWorks will use multi-agent orchestration to:

1. Summarize and review email, then create automated timelines and history.
2. Summarize and review Slack channels/messages, then create automated
   timelines and history.
3. Vectorize timelines, history, Slack evidence, email evidence, and internal
   company documents to build RAG for end users.
4. Support parallel development by three developers through clear backend,
   frontend, and agent/data boundaries.
5. Optimize LLM API token cost by design, without sacrificing answer quality or
   extraction reliability.

## Current State

Implemented foundation:

- FastAPI backend with source, document chunk, review, search, and permission
  models.
- Next.js frontend with Korean-first UX, Messenger, Review, Dashboard, Search,
  and Integrations routes.
- Slack connector boundary that maps Slack Web API-style payloads into
  `SourceEvent`.
- Deterministic `build_review_payloads` extractor that creates Review Queue
  candidates from chunks.
- Messenger-to-Review flow for the first "conversation to knowledge" product
  loop.

Missing before this vertical slice:

- LangChain/LangGraph dependencies are not yet installed.
- No provider-level LLM client abstraction exists.
- No token/cost accounting exists.
- No durable agent run model exists.
- No AI-generated timeline/history schema exists beyond generic `ReviewItem`
  payloads.

## External Framework Baseline

Use the current LangChain Python 1.x family and LangGraph 1.x family.

- LangGraph official installation uses `pip install -U langgraph` and commonly
  pairs with `langchain`; it requires Python 3.10+.
- LangChain 1.x positions `create_agent` as the standard agent interface and is
  built on LangGraph for deeper orchestration.
- LangChain/LangGraph 1.0 are documented as LTS lines with semver behavior
  inside the 1.x major version.

Sources checked on 2026-05-01:

- https://docs.langchain.com/oss/python/langgraph/install
- https://docs.langchain.com/oss/python/langchain/install
- https://docs.langchain.com/oss/python/releases/langchain-v1
- https://docs.langchain.com/oss/python/release-policy

Project dependency target:

```toml
langchain >= 1.2.0
langgraph >= 1.0.0
```

Provider packages should be installed separately, for example
`langchain-openai`, only when the chosen LLM provider is confirmed.

## Recommended Approach

Use an agent-runtime boundary with LangGraph orchestration behind a stable
ParaWorks interface.

Do not call LangChain/LangGraph directly from API routes, connector code, or
frontend-specific services. Instead, introduce:

```text
backend/app/agent_runtime/
  contracts.py
  cost_policy.py
  slack_timeline_graph.py
  model_router.py
  run_store.py
```

The ingestion layer still owns source normalization. The agent runtime receives
permission-filtered, bounded source packets and returns structured timeline and
history candidates. Review Queue remains the human-control gate before anything
becomes trusted knowledge.

## Alternatives Considered

### A. Direct LangChain Calls Inside Slack Sync

Pros:

- Fastest to code for a demo.
- Minimal new structure.

Cons:

- Hard to test.
- Token usage becomes hidden inside sync logic.
- Difficult for three developers to work in parallel.
- Weak boundary for future email and document agents.

Decision: reject.

### B. Full Multi-Agent Platform First

Pros:

- Most aligned with the final vision.
- Can model email, Slack, documents, RAG, scheduling, and review together.

Cons:

- Too much architecture before the first useful AI loop.
- Higher risk of expensive LLM calls without product validation.
- Hard to show a working portfolio milestone quickly.

Decision: defer.

### C. Slack Timeline Vertical Slice With Agent Runtime Boundary

Pros:

- Builds on the existing Slack connector, ingestion, and Review Queue.
- Produces visible product value quickly.
- Creates reusable contracts for future email and document agents.
- Makes token budgeting a first-class part of the runtime.

Cons:

- Requires a small architecture layer before visible behavior changes.
- Initial graph must stay narrow to avoid premature complexity.

Decision: choose this.

## Agent Workflow

The first LangGraph workflow should be deliberately small:

```text
CollectSlackEvidence
  -> CompressThreadOrChannelWindow
  -> ExtractTimelineCandidates
  -> ValidateEvidenceAndPermissions
  -> EstimateCostAndQuality
  -> CreateReviewItems
```

### CollectSlackEvidence

Input:

- Slack `SourceEvent` records or existing `DocumentChunk` records.
- Channel id, time window, permission level, and source URLs.

Output:

- A bounded evidence packet with message text, authors, timestamps, source
  links, snippets, and permission metadata.

Rules:

- Exclude messages the requesting user cannot access.
- Preserve source URLs and Slack timestamps.
- Group adjacent messages into windows before sending to the LLM.

### CompressThreadOrChannelWindow

Purpose:

- Reduce token use before extraction.
- Remove boilerplate and repeated acknowledgements.
- Keep all decision-critical sentences and disagreement signals.

Expected output:

- Korean summary by default.
- Important participants.
- Open questions.
- Evidence references back to source message ids.

Cost rule:

- Use deterministic compression where possible.
- Use a smaller/cheaper model for compression if LLM compression is necessary.

### ExtractTimelineCandidates

Purpose:

- Produce structured `history_event`, `timeline_event`, `decision_record`, and
  `todo` candidates from Slack evidence.

The output must include:

- title
- Korean summary
- event time or time range
- participants
- source snippets
- source links
- confidence score
- uncertainty reason when confidence is low

### ValidateEvidenceAndPermissions

Purpose:

- Reject candidates without source evidence.
- Downgrade confidence when evidence is weak.
- Carry the strictest permission level from all contributing messages.

Rules:

- No evidence, no Review Queue item.
- Restricted source in, restricted review item out.
- The agent cannot broaden visibility.

### EstimateCostAndQuality

Purpose:

- Record approximate input tokens, output tokens, model name, cost tier, cache
  hit/miss, and quality checks for each run.

Decision:

- If quality is below threshold, create a `needs_more_evidence` review candidate
  instead of pretending the timeline is reliable.

### CreateReviewItems

Purpose:

- Persist generated candidates as `ReviewItem(status="pending_review")`.
- Keep human review as the trust boundary.

## Cost Optimization Policy

Token cost optimization is mandatory and should be visible in code and docs.

Initial policy:

- Use source windows: summarize only the selected Slack channel/time range, not
  the whole workspace.
- Deduplicate repeated messages and bot noise before LLM calls.
- Use deterministic preprocessing before LLM summarization.
- Use a cheaper model for compression and a stronger model only for structured
  extraction when needed.
- Cache evidence packet hashes and agent outputs.
- Store token/cost metadata per agent run.
- Make re-run behavior explicit: reuse cached results unless source messages or
  prompt versions changed.
- Keep prompts short and schema-first.
- Prefer structured output to reduce retry loops.

Quality guard:

- Cost optimization must not remove source evidence, permission metadata, or
  uncertainty notes.
- A cheaper path is acceptable only when the Review Queue result remains
  evidence-backed and human-verifiable.

## Developer Split for Three People

### Developer 1: Agent Runtime and Slack Graph

Ownership:

- `backend/app/agent_runtime/`
- LangChain/LangGraph dependencies.
- Agent run contracts, graph nodes, model routing, prompt versioning, and token
  cost policy.

Deliverable:

- Slack evidence packet -> timeline/history review candidates.

### Developer 2: Data, Ingestion, and RAG Foundation

Ownership:

- Slack ingestion persistence.
- Timeline/history schemas.
- Vectorization pipeline.
- Permission-aware retrieval contracts.

Deliverable:

- Generated and reviewed knowledge can become RAG-ready records without
  leaking restricted content.

### Developer 3: Product UX and Review Workflow

Ownership:

- Frontend timeline/history screens.
- Review Queue improvements for AI-generated candidates.
- Agent run status and cost visibility.

Deliverable:

- Korean business user can understand what the AI found, why it found it, what
  evidence supports it, and how much the run roughly cost.

## MVP Scope for This Vertical Slice

In scope:

- Add dependency and runtime boundary for LangChain/LangGraph.
- Add a Slack timeline graph using mock/fake LLM clients in tests first.
- Generate timeline/history candidates into Review Queue.
- Record token/cost metadata, even if initial costs are estimated in tests.
- Add portfolio and runbook documentation.

Out of scope:

- Full Slack OAuth install flow.
- Production token vault.
- Email agent.
- Full document RAG UI.
- Autonomous write-back to Slack or email.
- Unreviewed AI content becoming official knowledge.

## Data Flow

1. User starts Slack sync or runs Slack timeline extraction.
2. Slack connector fetches messages and maps them to `SourceEvent`.
3. Ingestion persists sources, documents, versions, and chunks.
4. Agent runtime selects a bounded Slack evidence window.
5. LangGraph orchestrates compression, extraction, validation, and cost
   accounting.
6. The graph emits structured timeline/history candidates.
7. Candidates become Review Queue items with evidence and permission metadata.
8. Approved items later become searchable/RAG-ready company history.

## Testing Strategy

Backend tests:

- Fake Slack events create bounded evidence packets.
- Fake LLM output creates expected timeline/history Review Items.
- Missing evidence is rejected.
- Restricted Slack messages create restricted Review Items.
- Token/cost metadata is stored for each agent run.
- Cached evidence avoids repeated LLM calls.

Frontend tests or smoke checks:

- Review page clearly distinguishes AI-generated timeline/history candidates.
- Candidate evidence is visible.
- Korean copy is default.
- Cost metadata is visible enough for developers/admin users.

## Open Questions

These should be resolved before production-grade implementation:

- Which LLM provider is the default for development and demo?
- Should LangSmith tracing be enabled, disabled, or optional in local dev?
- What is the initial monthly or per-run token budget target?
- Which Slack channels are safe to ingest in a real demo workspace?
- Should vector storage begin with Postgres pgvector only, or also support an
  external vector DB later?

## Approval Status

The user approved starting with the recommended Slack vertical slice on
2026-05-01. Implementation should begin only after this spec is reviewed and an
implementation plan is written.

