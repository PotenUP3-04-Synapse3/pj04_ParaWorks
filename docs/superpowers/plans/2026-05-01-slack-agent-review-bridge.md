# Slack Agent Review Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect persisted Slack source chunks to the Slack Agent and save evidence-backed agent output as Review Queue items.

**Architecture:** Add a narrow service under `backend/app/agents/slack_agent/` that queries Slack `DocumentChunk` records, converts them into an `EvidencePacket`, runs the injected `SlackAgent`, and persists each `ReviewCandidate` as `ReviewItem(status="pending_review")`. The service keeps API routes and ingestion unchanged for now.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, existing agent runtime contracts.

---

## File Structure

- Create `backend/app/agents/slack_agent/service.py`
  - Query Slack source chunks.
  - Build `EvidencePacket`.
  - Run `SlackAgent`.
  - Persist `ReviewItem` rows with agent cost metadata.
- Modify `backend/app/agents/slack_agent/__init__.py`
  - Re-export bridge helpers.
- Create `backend/tests/test_slack_agent_review_bridge.py`
  - Test source-to-evidence conversion and persisted ReviewItem shape.
- Modify `docs/portfolio-log.md`
  - Record the first Slack Agent-to-Review bridge milestone.

## Task 1: Bridge Tests

**Files:**

- Create: `backend/tests/test_slack_agent_review_bridge.py`

- [ ] **Step 1: Write failing tests**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidencePacket, PermissionContext
from backend.app.agents.slack_agent import SlackAgent, SlackAgentModelResponse, create_slack_agent_review_items
from backend.app.models import Document, DocumentChunk, DocumentVersion, ReviewItem, Source


class FakeSlackModel:
    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        assert packet.source_type == 'slack'
        assert packet.strictest_permission == 'restricted'
        return SlackAgentModelResponse(
            title='Redis decision timeline',
            summary='Redis was selected for job progress updates.',
            item_type='history_event',
            confidence_score=0.88,
            input_tokens=700,
            output_tokens=140,
        )


def seed_slack_chunk(db: Session, permission_level: str = 'restricted') -> None:
    source = Source(
        source_type='slack',
        source_id='C123:1777600800.000100',
        source_url='https://example.slack.com/archives/C123/p1777600800000100',
        title='Slack message in C123',
        author='U123',
        permission_level=permission_level,
        raw_metadata={'ts': '1777600800.000100', 'channel_id': 'C123'},
    )
    db.add(source)
    db.flush()

    document = Document(source_id=source.id, title=source.title, current_version='v1')
    db.add(document)
    db.flush()

    version = DocumentVersion(document_id=document.id, version='v1', body='Redis로 진행 상태를 관리합니다.')
    db.add(version)
    db.flush()

    db.add(
        DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=0,
            text='Redis로 진행 상태를 관리합니다.',
            source_snippet='Redis로 진행 상태를 관리합니다.',
            permission_level=permission_level,
            metadata_={'source_url': source.source_url, 'source_type': 'slack'},
        )
    )
    db.commit()


def test_slack_agent_bridge_persists_review_item(db_session: Session) -> None:
    seed_slack_chunk(db_session)
    agent = SlackAgent(model=FakeSlackModel())

    created = create_slack_agent_review_items(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='C123:2026-05-01',
    )

    assert len(created) == 1
    stored = db_session.scalars(select(ReviewItem)).one()
    assert stored.status == 'pending_review'
    assert stored.item_type == 'history_event'
    assert stored.payload['title'] == 'Redis decision timeline'
    assert stored.payload['summary'] == 'Redis was selected for job progress updates.'
    assert stored.payload['agent_name'] == 'slack_agent'
    assert stored.payload['prompt_version'] == 'slack-timeline:v1'
    assert stored.payload['token_usage']['total_tokens'] == 840
    assert stored.payload['estimated_cost_usd'] > 0
    assert stored.permission_level == 'restricted'
    assert stored.source_links == ['https://example.slack.com/archives/C123/p1777600800000100']
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_review_bridge.py -v
```

Expected: fail because `create_slack_agent_review_items` is not exported.

## Task 2: Bridge Implementation

**Files:**

- Create: `backend/app/agents/slack_agent/service.py`
- Modify: `backend/app/agents/slack_agent/__init__.py`

- [ ] **Step 1: Implement query and conversion**

Select Slack chunks by joining `DocumentChunk` and `Source`, build
`EvidenceMessage` objects, then create one `EvidencePacket`.

- [ ] **Step 2: Run the injected Slack Agent**

Call `agent.run(packet)` and map each candidate to a `ReviewItem`.

- [ ] **Step 3: Persist cost and trace metadata**

Store `agent_name`, `prompt_version`, `cache_key`, `estimated_cost_usd`,
`token_usage`, `title`, `summary`, and `uncertainty_reason` in ReviewItem
payload.

- [ ] **Step 4: Verify focused test**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_review_bridge.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Verify backend suite**

Run:

```powershell
uv run pytest backend/tests -v
```

Expected: all backend tests pass.

## Task 3: Documentation and Commit

- [ ] Update `docs/portfolio-log.md`.
- [ ] Commit with `feat: connect slack agent to review queue`.

