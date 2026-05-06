# Agent Runtime Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first shared Agent Runtime contracts so Slack, Mail/Document, and RAG/Orchestrator agents can be developed equally without inventing incompatible payload shapes.

**Architecture:** Add a small pure-Python `backend/app/agent_runtime/` package with dataclass contracts, evidence validation, strict permission propagation, cache-key generation, and token cost estimation. This first slice does not call LangChain or LangGraph yet; it creates the stable boundary that those graphs will use.

**Tech Stack:** Python 3.12, FastAPI backend conventions, pytest, dataclasses, hashlib, decimal arithmetic.

---

## File Structure

- Create `backend/app/agent_runtime/__init__.py`
  - Re-export the shared runtime contracts and helper functions.
- Create `backend/app/agent_runtime/contracts.py`
  - Define `PermissionContext`, `EvidenceMessage`, `EvidencePacket`,
    `ReviewCandidate`, `TokenUsage`, `AgentRunCost`, and `AgentRunResult`.
- Create `backend/app/agent_runtime/cost_policy.py`
  - Define deterministic cache-key and estimated-cost helpers.
- Create `backend/tests/test_agent_runtime_contracts.py`
  - Test evidence validation, permission propagation, cache-key stability, and
    token-cost metadata behavior.
- Modify `docs/portfolio-log.md`
  - Record the collaboration guide and common runtime milestone.
- Modify `docs/superpowers/runbooks/session-handoff.md`
  - Link `AGENTS.md` as required context for future LLM workers.

## Task 1: Collaboration Guide

**Files:**

- Create: `AGENTS.md`
- Modify: `docs/portfolio-log.md`
- Modify: `docs/superpowers/runbooks/session-handoff.md`

- [ ] **Step 1: Add the repo-root assistant guide**

Create `AGENTS.md` with the ParaWorks product goal, equal agent ownership,
evidence-first rule, Review Queue boundary, permission/security rules, token
cost policy, LangChain/LangGraph usage rules, testing requirements, and
forbidden assistant behavior.

- [ ] **Step 2: Link it from handoff docs**

Add `AGENTS.md` to the Active Project context in
`docs/superpowers/runbooks/session-handoff.md`.

- [ ] **Step 3: Record portfolio impact**

Add a portfolio entry explaining that ParaWorks now has a collaboration and
compliance guide for multi-human, multi-assistant development.

## Task 2: Shared Runtime Contracts

**Files:**

- Create: `backend/tests/test_agent_runtime_contracts.py`
- Create: `backend/app/agent_runtime/__init__.py`
- Create: `backend/app/agent_runtime/contracts.py`
- Create: `backend/app/agent_runtime/cost_policy.py`

- [ ] **Step 1: Write the failing tests**

```python
from backend.app.agent_runtime import (
    AgentRunCost,
    EvidenceMessage,
    EvidencePacket,
    PermissionContext,
    ReviewCandidate,
    TokenUsage,
    build_evidence_cache_key,
    estimate_agent_run_cost,
)


def test_evidence_packet_keeps_strictest_permission() -> None:
    packet = EvidencePacket(
        source_type='slack',
        source_window='C123:2026-05-01',
        messages=[
            EvidenceMessage(
                source_id='C123:1',
                source_url='https://example.slack.com/archives/C123/p1',
                text='internal update',
                author='U1',
                timestamp='2026-05-01T09:00:00+09:00',
                permission_level='internal',
            ),
            EvidenceMessage(
                source_id='C123:2',
                source_url='https://example.slack.com/archives/C123/p2',
                text='restricted decision',
                author='U2',
                timestamp='2026-05-01T09:05:00+09:00',
                permission_level='restricted',
            ),
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )

    assert packet.strictest_permission == 'restricted'
    assert packet.source_links == [
        'https://example.slack.com/archives/C123/p1',
        'https://example.slack.com/archives/C123/p2',
    ]


def test_review_candidate_requires_evidence() -> None:
    candidate = ReviewCandidate(
        item_type='history_event',
        title='Redis decision discussed',
        summary='The team discussed queue architecture.',
        source_links=[],
        source_snippets=[],
        confidence_score=0.8,
        permission_level='internal',
    )

    try:
        candidate.validate_evidence()
    except ValueError as exc:
        assert str(exc) == 'review candidate requires source evidence'
    else:
        raise AssertionError('candidate without evidence should be rejected')


def test_evidence_cache_key_is_stable_and_prompt_versioned() -> None:
    packet = EvidencePacket(
        source_type='slack',
        source_window='C123:2026-05-01',
        messages=[
            EvidenceMessage(
                source_id='C123:1',
                source_url='https://example.slack.com/archives/C123/p1',
                text='launch review moved to Friday',
                author='U1',
                timestamp='2026-05-01T09:00:00+09:00',
                permission_level='internal',
            )
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )

    first = build_evidence_cache_key(packet, prompt_version='slack-timeline:v1')
    second = build_evidence_cache_key(packet, prompt_version='slack-timeline:v1')
    changed = build_evidence_cache_key(packet, prompt_version='slack-timeline:v2')

    assert first == second
    assert first != changed


def test_estimate_agent_run_cost_records_token_metadata() -> None:
    cost = estimate_agent_run_cost(
        model_name='gpt-test',
        token_usage=TokenUsage(input_tokens=1000, output_tokens=250),
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        cache_hit=False,
    )

    assert isinstance(cost, AgentRunCost)
    assert cost.model_name == 'gpt-test'
    assert cost.token_usage.total_tokens == 1250
    assert cost.estimated_cost_usd == 0.0003
    assert cost.cache_hit is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_agent_runtime_contracts.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'backend.app.agent_runtime'`.

- [ ] **Step 3: Add minimal implementation**

Create `contracts.py`, `cost_policy.py`, and `__init__.py` with pure-Python
dataclasses and helper functions that satisfy the tests.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
uv run pytest backend/tests/test_agent_runtime_contracts.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run backend suite**

Run:

```powershell
uv run pytest backend/tests -v
```

Expected: all backend tests pass.

## Task 3: Commit

**Files:**

- `AGENTS.md`
- `backend/app/agent_runtime/__init__.py`
- `backend/app/agent_runtime/contracts.py`
- `backend/app/agent_runtime/cost_policy.py`
- `backend/tests/test_agent_runtime_contracts.py`
- `docs/portfolio-log.md`
- `docs/superpowers/plans/2026-05-01-agent-runtime-contracts.md`
- `docs/superpowers/runbooks/session-handoff.md`

- [ ] **Step 1: Review staged scope**

Run:

```powershell
git status --short
git diff --stat
```

Ensure `frontend/.env.local.example` remains untracked and unstaged.

- [ ] **Step 2: Commit**

```powershell
git add -- AGENTS.md backend/app/agent_runtime backend/tests/test_agent_runtime_contracts.py docs/portfolio-log.md docs/superpowers/plans/2026-05-01-agent-runtime-contracts.md docs/superpowers/runbooks/session-handoff.md
git commit -m "feat: add agent runtime contracts"
```

