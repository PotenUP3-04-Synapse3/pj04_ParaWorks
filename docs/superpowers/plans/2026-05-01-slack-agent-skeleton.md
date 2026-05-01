# Slack Agent Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first Slack Agent skeleton that turns a shared `EvidencePacket` into evidence-backed `ReviewCandidate` objects inside an `AgentRunResult`.

**Architecture:** Create an isolated `backend/app/agents/slack_agent/` package owned by the Slack Agent track. It uses the shared `agent_runtime` contracts, exposes an `AgentManifest`, accepts a fake/model client through a protocol, preserves source evidence and strict permissions, estimates token cost, and does not call live LLM APIs.

**Tech Stack:** Python 3.12, dataclasses, Protocol, pytest.

---

## File Structure

- Create `backend/app/agents/__init__.py`
  - Makes agent packages explicit.
- Create `backend/app/agents/slack_agent/__init__.py`
  - Re-export `SLACK_AGENT_MANIFEST`, `SlackAgent`, and response contracts.
- Create `backend/app/agents/slack_agent/agent.py`
  - Implement the agent skeleton and fake-model protocol.
- Create `backend/tests/test_slack_agent.py`
  - Test manifest metadata, evidence-backed candidates, permission propagation,
    and cost metadata.
- Modify `docs/portfolio-log.md`
  - Record the first functional agent skeleton milestone.

## Task 1: Slack Agent Tests

**Files:**

- Create: `backend/tests/test_slack_agent.py`

- [ ] **Step 1: Write failing tests**

```python
from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.slack_agent import SLACK_AGENT_MANIFEST, SlackAgent, SlackAgentModelResponse


class FakeSlackModel:
    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        return SlackAgentModelResponse(
            title='Redis queue decision captured',
            summary='The team agreed to use Redis-backed queues for MVP job progress.',
            item_type='history_event',
            confidence_score=0.84,
            input_tokens=900,
            output_tokens=180,
        )


def build_packet(permission_level: str = 'internal') -> EvidencePacket:
    return EvidencePacket(
        source_type='slack',
        source_window='C123:2026-05-01',
        messages=[
            EvidenceMessage(
                source_id='C123:1777600800.000100',
                source_url='https://example.slack.com/archives/C123/p1777600800000100',
                text='Redis 기반 큐로 MVP 작업 진행 상태를 관리하기로 했습니다.',
                author='U123',
                timestamp='2026-05-01T09:00:00+09:00',
                permission_level=permission_level,
            )
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )


def test_slack_agent_manifest_declares_shared_contracts() -> None:
    assert SLACK_AGENT_MANIFEST.name == 'slack_agent'
    assert SLACK_AGENT_MANIFEST.input_contract == 'EvidencePacket'
    assert SLACK_AGENT_MANIFEST.output_contract == 'AgentRunResult'
    assert 'timeline_extraction' in SLACK_AGENT_MANIFEST.capabilities


def test_slack_agent_creates_evidence_backed_review_candidate() -> None:
    agent = SlackAgent(model=FakeSlackModel())

    result = agent.run(build_packet())

    assert result.agent_name == 'slack_agent'
    assert result.prompt_version == 'slack-timeline:v1'
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.item_type == 'history_event'
    assert candidate.title == 'Redis queue decision captured'
    assert candidate.source_links == ['https://example.slack.com/archives/C123/p1777600800000100']
    assert candidate.source_snippets == ['Redis 기반 큐로 MVP 작업 진행 상태를 관리하기로 했습니다.']
    assert candidate.permission_level == 'internal'
    assert result.cost.model_name == 'fake-slack-agent-model'
    assert result.cost.token_usage.total_tokens == 1080
    assert result.cache_key


def test_slack_agent_preserves_restricted_permission() -> None:
    agent = SlackAgent(model=FakeSlackModel())

    result = agent.run(build_packet(permission_level='restricted'))

    assert result.candidates[0].permission_level == 'restricted'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent.py -v
```

Expected: fail because `backend.app.agents.slack_agent` does not exist.

## Task 2: Slack Agent Skeleton

**Files:**

- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/slack_agent/__init__.py`
- Create: `backend/app/agents/slack_agent/agent.py`

- [ ] **Step 1: Implement minimal agent**

Implement:

- `SlackAgentModelResponse`
- `SlackAgentModel` protocol
- `SLACK_AGENT_MANIFEST`
- `SlackAgent.run(packet)`

Rules:

- Use `build_evidence_cache_key`.
- Use `estimate_agent_run_cost`.
- Create one `ReviewCandidate` from model output.
- Call `candidate.validate_evidence()`.
- Use `packet.strictest_permission`.
- Preserve `packet.source_links` and `packet.source_snippets`.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent.py -v
```

Expected: 3 passed.

- [ ] **Step 3: Run backend suite**

Run:

```powershell
uv run pytest backend/tests -v
```

Expected: all backend tests pass.

## Task 3: Documentation and Commit

**Files:**

- Modify: `docs/portfolio-log.md`

- [ ] **Step 1: Update portfolio log**

Record that the first functional agent skeleton now exists and is testable with
a fake LLM/model client.

- [ ] **Step 2: Commit**

Run:

```powershell
git add -- backend/app/agents backend/tests/test_slack_agent.py docs/portfolio-log.md docs/superpowers/plans/2026-05-01-slack-agent-skeleton.md
git commit -m "feat: add slack agent skeleton"
```

