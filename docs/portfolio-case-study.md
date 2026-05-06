# ParaWorks Portfolio Case Study

## 1. Project Summary

ParaWorks is a Korean-first multi-agent company memory platform inspired by
Slack-style collaboration. The MVP focuses on turning Slack messages, mail,
documents, and approved review items into searchable company memory.

The long-term goal is not just "chat with documents." ParaWorks separates raw
workplace evidence, AI-generated candidates, human review, approved knowledge,
and RAG answers so that the product can stay useful, auditable, and safe in a
business environment.

## 2. Problem

Team communication is fragmented across Slack, email, documents, and calendar
context. Important decisions and project history often exist only as scattered
messages. A useful AI agent must therefore:

- summarize and review Slack channel history;
- summarize and review email and internal documents;
- create timeline/history candidates with source evidence;
- require human approval before promoting AI output to company knowledge;
- retrieve approved knowledge through permission-aware RAG;
- control API token cost before calling expensive model or embedding providers.

## 3. Architecture Direction

The current implementation uses a shared agent runtime boundary under
`backend/app/agent_runtime/` and keeps API routes, connectors, and graph
orchestration separated.

Key architecture decisions:

- LangGraph orchestration is isolated behind the agent runtime instead of being
  called directly from API routes.
- Slack, mail/document, and RAG agents share the same review and evidence-first
  contract.
- AI-generated outputs are stored as Review Queue candidates first, not trusted
  knowledge.
- Approved review items are promoted into the knowledge library and then used
  by RAG.
- PostgreSQL + pgvector is the production vector storage direction, while
  SQLite smoke mode stays deterministic for local demos and tests.

Graph capture:

- SVG: `docs/assets/company-memory-langgraph.svg`
- PNG: `docs/assets/company-memory-langgraph.png`

## 4. Multi-Agent Ownership Model

The team is designed around equal ownership of agents rather than splitting
only frontend/backend layers.

- Developer A owns the Slack Agent: Slack sync, message summarization, channel
  evidence, and Review Queue candidates.
- Developer B owns the Mail and Document Agent: Gmail, Drive, document evidence,
  and document-backed history candidates.
- Developer C owns the RAG and Orchestrator Agent: LangGraph coordination,
  approved knowledge retrieval, permission-aware answers, and token-cost policy.

This split makes integration easier because every developer owns one vertical
business capability, while shared contracts stay in `backend/app/agent_runtime/`.

## 5. Cost Optimization Strategy

Token cost is treated as a product requirement, not an afterthought.

Implemented cost controls:

- incremental vector indexing with content-hash skips;
- indexing results expose indexed/skipped counts and saved embedding calls;
- deterministic smoke embeddings for tests and local demos;
- live embedding provider hidden behind a provider boundary;
- LangGraph execution cost plan before expensive agent nodes run;
- per-agent `run` or `skip` decisions with reasons and token estimates;
- empty evidence or empty question skips the relevant agent call and avoids
  misleading `AgentRun` records;
- runtime status endpoints do not trigger sync, embeddings, or LLM calls.

Portfolio talking point:

> I designed the system so that synchronization, review extraction, embedding,
> and answer generation each expose their own cost-control signal. This makes
> cost visible to operators and prevents "run all agents every time" behavior.

## 6. Security And Review Boundaries

Important guardrails:

- raw connector tokens are stored behind token references;
- API responses expose credential availability, not raw token references;
- runtime sync messages redact Slack tokens, token references, refresh tokens,
  and OAuth client secrets before reaching the frontend;
- restricted source evidence must remain restricted in downstream outputs;
- AI output cannot become official knowledge without human approval;
- tests use fake clients or deterministic models instead of live provider APIs.

This boundary is especially important because ParaWorks handles internal
business communication where hallucinated or source-less AI output would be
risky.

## 7. Frontend/Product Experience

The frontend was evolved from a plain MVP into a Korean-first Slack-like
workspace experience:

- dashboard, messages, integrations, review, agent runs, and search flows;
- language toggle for Korean/English business users;
- messenger-style conversation surface;
- integration cards for Slack, Gmail, Drive, and Calendar;
- runtime status panels for connector mode, credential state, latest sync, and
  cost policy;
- agent run observability and detail pages;
- company memory search and RAG answer flow.

## 8. Verification Evidence

Representative commands used during implementation:

- `uv run pytest backend/tests/test_company_memory_orchestration_service.py backend/tests/test_orchestration_api.py backend/tests/test_agent_runs_api.py -v`
- `uv run pytest backend/tests/test_integration_runtime_status.py -v`
- `uv run ruff check backend/app/agent_runtime/company_memory.py backend/tests/test_company_memory_orchestration_service.py`
- `uv run ruff check backend/app/api/v1/integrations.py backend/app/core/redaction.py backend/tests/test_integration_runtime_status.py`
- `npm run build`
- `npx playwright test e2e/visual-smoke.spec.ts --project=chromium-desktop`

## 9. Resume Bullet Draft

Built ParaWorks, a Korean-first multi-agent company memory platform that
orchestrates Slack, mail/document, and RAG agents with LangGraph-style runtime
contracts, human review promotion, pgvector-ready retrieval, incremental
embedding cost controls, and runtime security redaction for live connector
operations.
