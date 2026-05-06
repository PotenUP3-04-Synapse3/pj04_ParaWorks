# Agent Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `AgentManifest` and `AgentRegistry` so Slack, Mail/Document, and RAG/Orchestrator agents can be developed independently and integrated through stable contracts.

**Architecture:** Extend the pure-Python `backend/app/agent_runtime/` package with manifest metadata, duplicate-name protection, and lookup helpers. The registry does not run LangGraph yet; it is a thin integration contract that prevents agents from importing each other directly.

**Tech Stack:** Python 3.12, dataclasses, pytest.

---

## File Structure

- Modify `AGENTS.md`
  - Add branch/integration pipeline rules for multi-assistant development.
- Modify `backend/app/agent_runtime/contracts.py`
  - Add `AgentManifest`.
- Create `backend/app/agent_runtime/registry.py`
  - Add `AgentRegistry`.
- Modify `backend/app/agent_runtime/__init__.py`
  - Re-export `AgentManifest` and `AgentRegistry`.
- Create `backend/tests/test_agent_registry.py`
  - Test registration, duplicate rejection, and capability lookup.
- Modify `docs/portfolio-log.md`
  - Record integration-pipeline and registry milestone.
- Create this plan file.

## Task 1: Document Integration Pipeline

**Files:**

- Modify: `AGENTS.md`

- [ ] **Step 1: Add branching and integration rules**

Add a section explaining that assistants should not "just merge later." Document
the shared contract branch, per-agent feature branches, integration branch,
frequent green merges, contract tests, and human decision points.

## Task 2: Registry Contract

**Files:**

- Create: `backend/tests/test_agent_registry.py`
- Modify: `backend/app/agent_runtime/contracts.py`
- Create: `backend/app/agent_runtime/registry.py`
- Modify: `backend/app/agent_runtime/__init__.py`

- [ ] **Step 1: Write the failing tests**

```python
from backend.app.agent_runtime import AgentManifest, AgentRegistry


def test_registry_registers_and_resolves_agent_manifest() -> None:
    registry = AgentRegistry()
    manifest = AgentManifest(
        name='slack_agent',
        owner='Developer A',
        input_contract='EvidencePacket',
        output_contract='AgentRunResult',
        prompt_versions=('slack-timeline:v1',),
        supported_permissions=('internal', 'restricted'),
        capabilities=('timeline_extraction', 'history_generation'),
    )

    registry.register(manifest)

    assert registry.get('slack_agent') == manifest
    assert registry.names == ('slack_agent',)


def test_registry_rejects_duplicate_agent_names() -> None:
    registry = AgentRegistry()
    manifest = AgentManifest(
        name='slack_agent',
        owner='Developer A',
        input_contract='EvidencePacket',
        output_contract='AgentRunResult',
        prompt_versions=('slack-timeline:v1',),
        supported_permissions=('internal',),
        capabilities=('timeline_extraction',),
    )

    registry.register(manifest)

    try:
        registry.register(manifest)
    except ValueError as exc:
        assert str(exc) == 'agent already registered: slack_agent'
    else:
        raise AssertionError('duplicate agent name should be rejected')


def test_registry_finds_agents_by_capability() -> None:
    registry = AgentRegistry()
    registry.register(
        AgentManifest(
            name='slack_agent',
            owner='Developer A',
            input_contract='EvidencePacket',
            output_contract='AgentRunResult',
            prompt_versions=('slack-timeline:v1',),
            supported_permissions=('internal', 'restricted'),
            capabilities=('timeline_extraction',),
        )
    )
    registry.register(
        AgentManifest(
            name='rag_orchestrator_agent',
            owner='Developer C',
            input_contract='EvidencePacket',
            output_contract='AgentRunResult',
            prompt_versions=('rag-answer:v1',),
            supported_permissions=('internal', 'restricted'),
            capabilities=('rag_answering',),
        )
    )

    matches = registry.find_by_capability('rag_answering')

    assert [manifest.name for manifest in matches] == ['rag_orchestrator_agent']
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_agent_registry.py -v
```

Expected: fail because `AgentManifest` and `AgentRegistry` are not exported.

- [ ] **Step 3: Add minimal implementation**

Add `AgentManifest` to `contracts.py`, create `registry.py`, and re-export both
from `__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
uv run pytest backend/tests/test_agent_registry.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run backend suite**

Run:

```powershell
uv run pytest backend/tests -v
```

Expected: all backend tests pass.

## Task 3: Commit

**Files:**

- `AGENTS.md`
- `backend/app/agent_runtime/contracts.py`
- `backend/app/agent_runtime/registry.py`
- `backend/app/agent_runtime/__init__.py`
- `backend/tests/test_agent_registry.py`
- `docs/portfolio-log.md`
- `docs/superpowers/plans/2026-05-01-agent-registry.md`

- [ ] **Step 1: Confirm scope**

Run:

```powershell
git status --short
git diff --stat
```

Confirm `frontend/.env.local.example` remains unstaged if it appears.

- [ ] **Step 2: Commit**

```powershell
git add -- AGENTS.md backend/app/agent_runtime backend/tests/test_agent_registry.py docs/portfolio-log.md docs/superpowers/plans/2026-05-01-agent-registry.md
git commit -m "feat: add agent registry contract"
```

