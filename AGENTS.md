# ParaWorks Agent Collaboration Guide

This repository is developed by multiple humans and multiple coding assistants
such as Codex, Claude Code, and Gemini. Follow this guide before changing code.

## Product Goal

ParaWorks is a Korean-first, multi-agentic company memory platform.

The final system uses LangChain 1.x and LangGraph 1.x to orchestrate agents
that:

- summarize and review email, then create timeline/history candidates;
- summarize and review Slack channels/messages, then create timeline/history
  candidates;
- vectorize reviewed history, timelines, Slack evidence, email evidence, and
  internal documents for permission-aware RAG;
- optimize LLM API token cost without weakening evidence quality,
  permissions, or reviewability.

## Equal Agent Ownership Model

The three developers should each own an agent, not only a technical layer.

- Developer A: Slack Agent
  - Slack channel/message summarization
  - conversation window compression
  - decision/history/todo candidate extraction
  - Review Queue integration

- Developer B: Mail and Document Agent
  - email summarization and review
  - internal document parsing and summarization
  - document-backed history candidates
  - source/version evidence preservation

- Developer C: RAG and Orchestrator Agent
  - reviewed knowledge retrieval
  - LangGraph orchestration between agents
  - permission-aware answer generation
  - token-cost routing, caching, and model selection policy

Shared runtime contracts belong in `backend/app/agent_runtime/`. Keep them small,
well-tested, and stable.

## Required Context Check

Before starting work, read or inspect:

- `docs/portfolio-log.md`
- `docs/superpowers/runbooks/session-handoff.md`
- the latest relevant spec under `docs/superpowers/specs/`
- the latest relevant plan under `docs/superpowers/plans/`
- `git status --short`

Never revert user or teammate changes unless explicitly asked.

## Development Workflow

Use this flow for non-trivial work:

```text
spec -> implementation plan -> failing test -> implementation -> verification -> commit
```

For behavior changes, use TDD. Watch the test fail before adding production
code. Do not claim completion without fresh verification output.

## Shared Agent Contracts

All agents should use shared concepts instead of inventing local payload shapes:

- `AgentInput`
- `AgentOutput`
- `EvidencePacket`
- `ReviewCandidate`
- `AgentRunCost`
- `PermissionContext`

If a shared contract changes, document the impact and update affected tests.

## Evidence-First Rule

AI output is not trusted knowledge by default.

Every timeline, history, decision, todo, or answer candidate must include:

- source links;
- source snippets;
- source identifiers such as Slack timestamp, email id, or document version;
- confidence score;
- permission level;
- uncertainty reason when confidence is low.

No evidence means no Review Queue item.

## Human Review Boundary

LLM-generated content must pass through the Review Queue before it becomes
trusted company knowledge.

Do not store agent output directly as official knowledge. Create
`ReviewItem(status="pending_review")` and preserve evidence metadata.

## Permission and Security Rules

- Filter inputs before sending data to an LLM.
- Keep the strictest permission level from all source evidence.
- An agent may narrow visibility but must never broaden it.
- Restricted source in means restricted output out.
- Never commit secrets, `.env` files, Slack tokens, OAuth tokens, or provider
  API keys.
- Avoid logging raw sensitive content. Prefer ids, hashes, counts, and short
  snippets when debugging.

## Token Cost Policy

Token cost is a product requirement.

Every agent design should consider:

- source windowing instead of whole-workspace prompts;
- deduplication and deterministic preprocessing before LLM calls;
- cheap compression model before stronger extraction model where appropriate;
- structured output to reduce retries;
- prompt versioning;
- evidence hash based caching;
- token input/output accounting;
- estimated cost metadata on every agent run.

Cost optimization must not remove source evidence, permission metadata, or
uncertainty notes.

## LangChain and LangGraph Rules

- Do not call LangChain or LangGraph directly from API routes or connectors.
- Put orchestration behind `backend/app/agent_runtime/`.
- Keep graph nodes small and testable.
- Use fake LLM/model clients in tests.
- Keep provider packages replaceable through a model-router boundary.
- Use LangChain >= 1.2.0 and LangGraph 1.x when agent dependencies are added.

## Testing Requirements

Agent-related changes should test:

- missing evidence is rejected;
- restricted source remains restricted;
- Review Queue payloads preserve source links and snippets;
- token/cost metadata is recorded;
- cache hits avoid repeated LLM calls;
- prompt version changes invalidate cached agent output;
- fake LLM output can drive the graph without live provider calls.

## Documentation Requirements

Update `docs/portfolio-log.md` whenever the product story, architecture, demo
flow, or verification evidence changes.

Update `docs/superpowers/runbooks/session-handoff.md` when future workers need
new context to continue safely.

## Forbidden Assistant Behavior

Coding assistants must not:

- overwrite unrelated user or teammate work;
- perform broad refactors outside the assigned ownership area;
- break shared contracts without documenting migration impact;
- call live LLM APIs in tests;
- commit secrets;
- claim tests/builds pass without running them in the current session;
- promote source-less AI output to trusted knowledge.

