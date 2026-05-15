# Slack 프로젝트 Tool Routing 통합 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slack 업무 후보의 프로젝트 연결을 전부 LangChain tool 기반 LLM 판단으로 통합하고, 프로젝트가 지정되지 않은 검토 후보는 승인할 수 없게 하며, 승인 후 타임라인/프로젝트 탭에 프로젝트별 활동이 안정적으로 표시되게 한다.

**Architecture:** 신규 Slack sync에서는 규칙 기반 `project_assignment` ReviewItem을 만들지 않는다. Slack Agent의 LangGraph `project_route` 노드가 등록 프로젝트 목록을 tool로 확인하고, `decision_record`, `todo`, `history_event` 후보 payload에 프로젝트 선택/미선택 상태를 붙인다. Review 승인 경계에서 Slack Agent 후보는 등록 프로젝트가 반드시 있어야 trusted knowledge로 승격되며, 승격된 지식은 기존 `TimelineEvent`, `DecisionRecord`, `HistoryEvent`, `Todo`의 `project_key`로 프로젝트/타임라인 화면에 연결된다.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, LangChain tool-calling, LangGraph, Pydantic v2, pytest, Next.js/React/TypeScript, Playwright.

---

## 현재 문제 정리

1. `backend/app/projects/classifier.py`가 `project_assignment`를 규칙 기반 alias matching으로 생성한다.
2. `agent_slack/project_routing.py`와 `agent_slack/agent_slack.py`에는 이미 LangChain tool 기반 프로젝트 라우팅 노드가 있지만, `backend/app/agents/slack_agent/sync_service.py`가 `topic_tag` 기반 fallback `_determine_project_from_tag()`를 계속 섞고 있다.
3. `backend/app/api/v1/integrations.py`와 `backend/app/api/v1/projects.py`가 아직 `create_project_assignment_review_items()`를 호출할 수 있어 Slack source에서 규칙 기반 프로젝트 연결 후보가 다시 생길 수 있다.
4. `backend/app/knowledge/promotion.py`는 `todo`, `decision_record`, `history_event`, `timeline_event` 승인을 프로젝트 없이도 허용한다.
5. `frontend/src/app/review/page.tsx`는 프로젝트 미선택 상태를 보여줄 수 있지만, “프로젝트가 필요해서 승인 불가”를 충분히 강조하지 않는다.
6. `frontend/src/app/timeline/page.tsx`는 프로젝트별 timeline item을 표시하지만 날짜 단위 그룹이 없다.
7. `frontend/src/app/projects/page.tsx`는 모바일/좁은 폭에서 `근거`, `활동`, `검토 대기` metric 영역이 겹칠 수 있다.

## 범위

- 이번 구현 범위는 Slack sync -> Slack Agent -> Review -> 승인 -> Timeline/Projects 표시까지다.
- Gmail/Drive의 프로젝트 분류도 궁극적으로 같은 `ProjectRoutingDecision` 계약을 쓰는 것이 맞지만, Developer B 소유 영역이므로 이번 계획에서는 기존 deterministic 분류를 더 확장하지 않고 Slack 신규 생성 경로에서 제거하는 데 집중한다.
- 기존 DB에 이미 남아 있는 `project_assignment` 항목은 마이그레이션/정리 작업 대상이다. 이번 구현은 “새로 생성되는 Slack 검토 후보”가 규칙 기반 `project_assignment`로 다시 오염되지 않게 하는 것을 우선한다.

## 파일 구조

- Modify: `agent_slack/project_routing.py`
  - 프로젝트 match / no match 결과 계약을 명확히 하고, tool 사용 규칙을 강화한다.
- Modify: `agent_slack/agent_slack.py`
  - 모든 Slack 후보에 project routing 상태를 붙인다.
  - 프로젝트를 확정하지 못한 후보는 `project_key`를 비워두고 `project_needs_user_selection=true`로 둔다.
- Modify: `backend/app/agents/slack_agent/sync_service.py`
  - `_determine_project_from_tag()` fallback을 Slack Agent 저장 경로에서 제거한다.
  - ReviewItem payload는 project router 결과만 신뢰한다.
- Modify: `backend/app/api/v1/integrations.py`
  - Slack sync에서는 `create_project_assignment_review_items()`를 호출하지 않는다.
  - 응답의 `project_assignment_items`는 Slack에서는 항상 0으로 유지한다.
- Modify: `backend/app/api/v1/projects.py`
  - 새 프로젝트 생성 직후 규칙 기반 Slack project assignment를 만들지 않는다.
  - `/projects/reclassify`는 기존 deterministic 경로임을 명확히 하거나 Slack source를 제외한다.
- Modify: `backend/app/projects/classifier.py`
  - Slack source를 deterministic `project_assignment` 후보 생성 대상에서 제외한다.
  - 가능하면 함수 이름/metadata에 legacy deterministic classifier임을 남긴다.
- Modify: `backend/app/knowledge/promotion.py`
  - Slack Agent가 만든 promotable item은 등록 프로젝트가 없으면 승인 불가로 만든다.
- Modify: `backend/app/api/v1/review.py`
  - `PATCH /review/{id}`의 project validation은 유지한다.
  - promotion preview가 `project_key` 누락을 정확히 내려주는지 테스트로 고정한다.
- Modify: `backend/app/projects/service.py`
  - `pending_review_count`가 `project_assignment`만 세지 않도록, project_key가 붙은 모든 pending Slack Agent 후보를 세도록 바꾼다.
- Modify: `frontend/src/app/review/page.tsx`
  - 프로젝트 미지정 Slack Agent 후보에 “프로젝트 선택 후 승인 가능” 안내를 표시한다.
  - `canApprove=false`이면 승인 버튼이 비활성화되고 이유가 보이게 한다.
  - 필요 시 “새 프로젝트 만들기” 링크를 프로젝트 탭으로 연결한다.
- Modify: `frontend/src/app/timeline/page.tsx`
  - 승인된 프로젝트 타임라인을 날짜 단위로 그룹 표시한다.
- Modify: `frontend/src/app/projects/page.tsx`
  - metric 영역 겹침을 방지하고 모바일 레이아웃을 안정화한다.
- Test: `backend/tests/test_agent_slack_pipeline_quality.py`
- Test: `backend/tests/test_slack_agent_api.py`
- Test: `backend/tests/test_mock_sync.py`
- Test: `backend/tests/test_project_memory_api.py`
- Test: `backend/tests/test_review.py`
- Test: `frontend/e2e/review-project-routing-required.spec.ts`
- Test: `frontend/e2e/timeline-project-date-groups.spec.ts`
- Test: `frontend/e2e/projects-responsive-metrics.spec.ts`
- Test: `frontend/e2e/slack-project-routing-flow.spec.ts`

---

## Task 1: Project Router 결과 계약 강화

**Files:**
- Modify: `agent_slack/project_routing.py`
- Modify: `agent_slack/agent_slack.py`
- Test: `backend/tests/test_agent_slack_pipeline_quality.py`

- [ ] **Step 1: failing test 작성**

`backend/tests/test_agent_slack_pipeline_quality.py`에 다음 테스트를 추가한다.

```python
def test_agent_slack_routes_every_candidate_and_marks_unmatched_for_user_selection() -> None:
    class FakeProjectRouter:
        def invoke(self, payload):
            return {
                'model_name': 'fake-router',
                'input_tokens': 12,
                'output_tokens': 9,
                'decisions': [
                    {
                        'source_id': 'C123:candidate-0',
                        'item_index': 0,
                        'project_key': 'project-alpha',
                        'project_name': 'Project Alpha',
                        'confidence_score': 0.9,
                        'assignment_summary': 'Redis 큐 안정화 활동입니다.',
                        'assignment_reason': 'Redis와 sync job 단서가 Project Alpha와 일치합니다.',
                        'alternatives': [],
                        'needs_user_selection': False,
                    },
                    {
                        'source_id': 'C123:candidate-1',
                        'item_index': 1,
                        'project_key': None,
                        'project_name': None,
                        'confidence_score': 0.41,
                        'assignment_summary': '등록 프로젝트와 직접 일치하지 않습니다.',
                        'assignment_reason': '프로젝트 이름/설명과 매칭되는 근거가 부족합니다.',
                        'alternatives': ['Project Alpha'],
                        'needs_user_selection': True,
                    },
                ],
            }

    candidates = [
        ReviewCandidate(
            title='Redis 큐 점검',
            summary='Redis 큐 상태를 확인했습니다.',
            item_type='history_event',
            source_links=[],
            source_snippets=['Redis 큐 상태 확인'],
            confidence_score=0.86,
            permission_level='internal',
        ),
        ReviewCandidate(
            title='새 캠페인 킥오프',
            summary='아직 등록되지 않은 캠페인 논의입니다.',
            item_type='todo',
            source_links=[],
            source_snippets=['새 캠페인 준비 필요'],
            confidence_score=0.82,
            permission_level='internal',
        ),
    ]
    state = SlackAgentState(
        channel_id='C123',
        candidates=candidates,
        projects=[ProjectOption(project_key='project-alpha', name='Project Alpha', summary='Redis sync work')],
        project_router_model=FakeProjectRouter(),
    )

    result = project_route_node(state)

    first, second = result['candidates']
    assert first.payload_fields['project_key'] == 'project-alpha'
    assert first.payload_fields['project_assignment_method'] == 'llm_tool'
    assert first.payload_fields['project_needs_user_selection'] is False
    assert 'project_key' not in second.payload_fields
    assert second.payload_fields['project_assignment_method'] == 'llm_tool'
    assert second.payload_fields['project_needs_user_selection'] is True
    assert second.payload_fields['project_assignment_reason'] == '프로젝트 이름/설명과 매칭되는 근거가 부족합니다.'
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_pipeline_quality.py::test_agent_slack_routes_every_candidate_and_marks_unmatched_for_user_selection -q
```

Expected: 현재 source id fallback이나 decision 적용 방식이 테스트 기대와 다르면 실패한다.

- [ ] **Step 3: 최소 구현**

`agent_slack/project_routing.py`의 `route_projects_for_candidates()` rules를 다음 의미로 보강한다.

```python
'등록 프로젝트에 해당한다고 판단한 경우에만 project_key를 채우세요.',
'근거가 부족하거나 새 프로젝트가 필요해 보이면 project_key를 null로 두고 needs_user_selection=true로 두세요.',
'모든 candidate_items에 대해 decisions 항목을 하나씩 반환하세요.',
```

`agent_slack/agent_slack.py`의 `_apply_project_routing_decisions()`는 현재 방식처럼 `decision.project_key`가 있을 때만 `project_key`를 넣고, 없으면 절대 fallback project를 넣지 않는다.

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_pipeline_quality.py::test_agent_slack_routes_every_candidate_and_marks_unmatched_for_user_selection -q
```

Expected: `1 passed`.

---

## Task 2: Slack 저장 경로에서 규칙 기반 project fallback 제거

**Files:**
- Modify: `backend/app/agents/slack_agent/sync_service.py`
- Test: `backend/tests/test_slack_agent_api.py`

- [ ] **Step 1: failing test 작성**

`backend/tests/test_slack_agent_api.py`에 다음 테스트를 추가한다.

```python
def test_slack_agent_review_item_uses_only_tool_project_routing(monkeypatch, client, db_session) -> None:
    db_session.add(Project(project_key='project-alpha', name='Project Alpha', summary='Redis work'))
    db_session.commit()

    def fake_process_daily_slack_sync(*args, **kwargs):
        return {
            'is_work_related': True,
            'model_name': 'gpt-5-mini',
            'project_model_name': 'fake-router',
            'project_prompt_tokens': 10,
            'project_completion_tokens': 5,
            'run_cost': AgentRunCost(
                model_name='gpt-5-mini',
                token_usage=TokenUsage(input_tokens=100, output_tokens=50),
                estimated_cost_usd=0.0001,
                cache_hit=False,
            ),
            'candidates': [
                ReviewCandidate(
                    title='등록 프로젝트 없음',
                    summary='topic_tag에는 Project Alpha가 있어도 router가 매칭하지 않았습니다.',
                    item_type='history_event',
                    source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
                    source_snippets=['새 프로젝트 후보입니다.'],
                    confidence_score=0.8,
                    permission_level='internal',
                    payload_fields={
                        'topic_tag': 'Project Alpha',
                        'project_assignment_method': 'llm_tool',
                        'project_assignment_summary': '등록 프로젝트와 확정 매칭되지 않습니다.',
                        'project_assignment_reason': 'router가 사용자 선택 필요로 판단했습니다.',
                        'project_assignment_confidence': 0.41,
                        'project_needs_user_selection': True,
                    },
                ),
            ],
        }

    monkeypatch.setattr(
        'backend.app.agents.slack_agent.sync_service.process_daily_slack_sync',
        fake_process_daily_slack_sync,
    )
    client.post('/api/v1/integrations/slack/sync')

    item = db_session.query(ReviewItem).filter_by(item_type='history_event').one()
    assert item.payload['project_assignment_method'] == 'llm_tool'
    assert item.payload['project_needs_user_selection'] is True
    assert item.payload.get('project_key') in (None, '')
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_review_item_uses_only_tool_project_routing -q
```

Expected: 현재 `sync_service.py`가 `_determine_project_from_tag()` fallback으로 `project_key`를 채워 실패한다.

- [ ] **Step 3: 최소 구현**

`backend/app/agents/slack_agent/sync_service.py`에서 다음을 제거한다.

```python
from backend.app.agents.slack_agent.service import (
    _determine_project_from_tag,
    back_propagate_slack_tags,
)
back_propagate_slack_tags(db, candidate)
project_key, is_new_project = _determine_project_from_tag(topic_tag, candidate.summary)
```

payload 구성은 다음 계약을 따른다.

```python
payload = {
    'title': candidate.title,
    'summary': candidate.summary,
    'category': candidate.payload_fields.get('category', 'Ad-hoc'),
    'topic_tag': topic_tag,
    'importance': candidate.payload_fields.get('importance', 'Medium'),
    'assignee': candidate.payload_fields.get('assignee', '미지정'),
    'due_date': candidate.payload_fields.get('due_date', '기한없음'),
    'project_key': project_fields.get('project_key'),
    'project_name': project_fields.get('project_name'),
    'is_new_project': False,
    'agent_run_id': agent_run.id,
    'agent_name': 'slack_agent',
    'prompt_version': agent_run.prompt_version,
    'estimated_cost_usd': agent_run.estimated_cost_usd,
    'source_ids': source_ids,
    'source_authors': source_authors,
    **project_fields,
}
```

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_review_item_uses_only_tool_project_routing -q
```

Expected: `1 passed`.

---

## Task 3: Slack에서 신규 규칙 기반 `project_assignment` 생성 중단

**Files:**
- Modify: `backend/app/api/v1/integrations.py`
- Modify: `backend/app/api/v1/projects.py`
- Modify: `backend/app/projects/classifier.py`
- Test: `backend/tests/test_mock_sync.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: failing tests 작성**

`backend/tests/test_mock_sync.py`에 다음 테스트를 추가한다.

```python
def test_slack_sync_does_not_create_project_assignment_review_items(client, db_session) -> None:
    db_session.add(Project(project_key='project-alpha', name='Project Alpha', summary='Slack Redis sync'))
    db_session.commit()

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert response.json()['project_assignment_items'] == 0
    assert db_session.query(ReviewItem).filter_by(item_type='project_assignment').count() == 0
```

`backend/tests/test_project_memory_api.py`에 다음 테스트를 추가한다.

```python
def test_project_define_does_not_backfill_slack_project_assignments(client, db_session) -> None:
    source = Source(
        source_type='slack',
        source_id='C123:1777600800.000100',
        source_url='https://example.slack.com/archives/C123/p1777600800000100',
        title='Project Alpha Slack message',
        author='user@example.com',
        permission_level='internal',
        raw_metadata={'channel_id': 'C123', 'ts': '1777600800.000100'},
    )
    db_session.add(source)
    db_session.commit()

    response = client.post('/api/v1/projects/define', json={'name': 'Project Alpha', 'summary': 'Slack Redis sync'})

    assert response.status_code == 200
    assert response.json()['created_review_items'] == 0
    assert db_session.query(ReviewItem).filter_by(item_type='project_assignment').count() == 0
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mock_sync.py::test_slack_sync_does_not_create_project_assignment_review_items backend/tests/test_project_memory_api.py::test_project_define_does_not_backfill_slack_project_assignments -q
```

Expected: 기존 코드가 Slack source 기반 `project_assignment`를 만들면 실패한다.

- [ ] **Step 3: 최소 구현**

`backend/app/projects/classifier.py`에서 Slack을 deterministic 대상에서 제거한다.

```python
PROJECT_SOURCE_TYPES = ('gmail', 'gmail_attachment', 'drive', 'calendar')
```

`backend/app/api/v1/integrations.py`의 Slack connector branch는 `create_project_assignment_review_items(db)`를 호출하지 않는다. Gmail/Drive/Calendar는 이번 범위에서 유지하되, 응답 metadata에 Slack은 `project_assignment_items=0`임을 유지한다.

`backend/app/api/v1/projects.py`의 `define_project()`는 새 프로젝트 생성 직후 Slack deterministic backfill이 생기지 않도록 위 classifier 변경에 의존한다. 응답의 `created_review_items`는 실제 생성 수를 반환한다.

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mock_sync.py::test_slack_sync_does_not_create_project_assignment_review_items backend/tests/test_project_memory_api.py::test_project_define_does_not_backfill_slack_project_assignments -q
```

Expected: `2 passed`.

---

## Task 4: Slack Agent 후보는 프로젝트 선택 전 승인 불가

**Files:**
- Modify: `backend/app/knowledge/promotion.py`
- Modify: `backend/app/api/v1/review.py`
- Test: `backend/tests/test_review.py`

- [ ] **Step 1: failing test 작성**

`backend/tests/test_review.py`에 다음 테스트를 추가한다.

```python
def test_slack_agent_review_item_requires_project_before_approval(client, db_session) -> None:
    db_session.add(Project(project_key='project-alpha', name='Project Alpha', summary='Redis work'))
    item = ReviewItem(
        item_type='history_event',
        payload={
            'title': '등록 프로젝트 확인 필요',
            'summary': 'Slack Agent가 업무 후보로 판단했지만 프로젝트 선택이 필요합니다.',
            'agent_name': 'slack_agent',
            'project_assignment_method': 'llm_tool',
            'project_needs_user_selection': True,
        },
        source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
        source_snippets=['새 프로젝트로 보이는 업무 논의입니다.'],
        confidence_score=0.82,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    preview = client.get(f'/api/v1/review/{item.id}/promotion-preview')
    blocked = client.post(f'/api/v1/review/{item.id}/approve')
    patched = client.patch(f'/api/v1/review/{item.id}', json={'payload': {'project_key': 'project-alpha'}})
    approved = client.post(f'/api/v1/review/{item.id}/approve')

    assert preview.status_code == 200
    assert preview.json()['can_approve'] is False
    assert 'project_key' in preview.json()['missing_required_fields']
    assert blocked.status_code == 400
    assert patched.status_code == 200
    assert patched.json()['payload']['project_name'] == 'Project Alpha'
    assert approved.status_code == 200
    assert approved.json()['promotion_result']['project_key'] == 'project-alpha'
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_review.py::test_slack_agent_review_item_requires_project_before_approval -q
```

Expected: 현재는 프로젝트 없이 승인 가능해서 실패한다.

- [ ] **Step 3: 최소 구현**

`backend/app/knowledge/promotion.py`에 helper를 추가한다.

```python
def _requires_project_key(item: ReviewItem) -> bool:
    return (
        item.item_type in PROMOTABLE_REVIEW_TYPES
        and item.payload.get('agent_name') == 'slack_agent'
        and item.payload.get('project_assignment_method') == 'llm_tool'
    )
```

`build_promotion_preview()`에서 `normalized_payload`에 `project_key`를 포함한다.

```python
if _requires_project_key(item):
    normalized_payload['project_key'] = _string_payload(item, 'project_key')
```

`_required_fields_for_item(item)` 형태로 기존 `_required_fields_for_type()`을 확장하고, Slack Agent LLM tool-routed item이면 `project_key`를 추가한다.

```python
def _required_fields_for_item(item: ReviewItem) -> tuple[str, ...]:
    fields = list(_required_fields_for_type(item.item_type))
    if _requires_project_key(item):
        fields.append('project_key')
    return tuple(fields)
```

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_review.py::test_slack_agent_review_item_requires_project_before_approval -q
```

Expected: `1 passed`.

---

## Task 5: Review UI에서 프로젝트 선택 필요 상태 표시

**Files:**
- Modify: `frontend/src/app/review/page.tsx`
- Test: `frontend/e2e/review-project-routing-required.spec.ts`

- [ ] **Step 1: Playwright failing test 작성**

`frontend/e2e/review-project-routing-required.spec.ts`를 만든다.

```ts
import { expect, test } from "@playwright/test";

const item = {
  id: 501,
  item_type: "history_event",
  payload: {
    title: "새 캠페인 킥오프",
    summary: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.",
    agent_name: "slack_agent",
    project_assignment_method: "llm_tool",
    project_assignment_summary: "등록된 프로젝트와 직접 일치하지 않습니다.",
    project_assignment_reason: "프로젝트 설명과 일치하는 근거가 부족해 사용자 선택이 필요합니다.",
    project_assignment_confidence: 0.41,
    project_needs_user_selection: true,
  },
  source_links: ["https://example.slack.com/archives/C123/p1777600800000100"],
  source_snippets: ["새 캠페인 준비 논의"],
  source_evidence: [],
  agent_run_id: 1,
  agent_run_details: {
    model_name: "gpt-5-mini",
    prompt_version: "slack-taxonomy:v3",
    estimated_cost_usd: 0.0001,
    total_tokens: 150,
  },
  confidence_score: 0.82,
  permission_level: "internal",
  status: "pending_review",
  reviewer_id: null,
};

test("Slack LLM routed item requires project selection before approval", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ contentType: "application/json", json: { user: { id: "demo-admin", email: "admin@paraworks.com", role: "admin", permission_levels: ["public", "internal", "restricted"], name: "Admin", title: "Admin", department: "Platform" } } }));
  await page.route("**/api/v1/notifications", route => route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } }));
  await page.route("**/api/v1/dashboard", route => route.fulfill({ contentType: "application/json", json: { pending_review_count: 1, source_counts: { slack: 1, gmail: 0, drive: 0, calendar: 0, other: 0 } } }));
  await page.route("**/api/v1/projects/defined", route => route.fulfill({ contentType: "application/json", json: { projects: [{ project_key: "project-alpha", name: "Project Alpha" }] } }));
  await page.route("**/api/v1/review?status=pending_review**", route => route.fulfill({ contentType: "application/json", json: { groups: [{ group_id: "history_event:새 캠페인 킥오프", title: "새 캠페인 킥오프", item_type: "history_event", status: "pending_review", permission_level: "internal", items: [item], total_count: 1, avg_confidence: 0.82 }], items: [item], total_count: 1, limit: 50, offset: 0, has_more: false, include_previews: false } }));
  await page.route("**/api/v1/review/501/promotion-preview", route => route.fulfill({ contentType: "application/json", json: { target_type: "history_event", can_approve: false, missing_required_fields: ["project_key"], normalized_payload: { title: "새 캠페인 킥오프", reason: "등록 프로젝트와 확정 매칭되지 않은 Slack 업무 후보입니다.", project_key: "" } } }));
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/review");
  await page.locator(".group-container > div:first-child").click();

  await expect(page.getByText("프로젝트 선택 후 승인 가능")).toBeVisible();
  await expect(page.getByText("새 프로젝트 만들기")).toBeVisible();
  await expect(page.getByRole("button", { name: "승인" })).toBeDisabled();
  await expect(page.getByLabel("프로젝트 지정")).toHaveValue("");
});
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
npm.cmd run test:visual -- review-project-routing-required.spec.ts --project=chromium-desktop
```

Expected: 현재 안내/disabled 계약이 부족하면 실패한다.

- [ ] **Step 3: 최소 구현**

`frontend/src/app/review/page.tsx`에 helper를 추가한다.

```ts
function needsProjectSelection(item: ReviewItem, preview?: ReviewPromotionPreview) {
  return (
    item.payload.project_assignment_method === "llm_tool" &&
    (!stringField(item.payload.project_key) || preview?.missing_required_fields?.includes("project_key"))
  );
}
```

프로젝트 select 아래에 표시한다.

```tsx
{needsProjectSelection(item, preview) ? (
  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
    프로젝트 선택 후 승인 가능
    <Link href="/projects" className="ml-2 underline underline-offset-4">새 프로젝트 만들기</Link>
  </div>
) : null}
```

승인 버튼은 기존 `canApprove`를 사용해 disabled 상태가 되도록 유지하고, disabled 이유 텍스트가 보이게 한다.

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
npm.cmd run test:visual -- review-project-routing-required.spec.ts
```

Expected: desktop/mobile `2 passed`.

---

## Task 6: 승인 후 프로젝트 타임라인/프로젝트 탭 연결 보강

**Files:**
- Modify: `backend/app/projects/service.py`
- Test: `backend/tests/test_project_memory_api.py`
- Test: `backend/tests/test_review.py`

- [ ] **Step 1: failing test 작성**

`backend/tests/test_project_memory_api.py`에 다음 테스트를 추가한다.

```python
def test_slack_tool_routed_approved_items_appear_in_project_activity_and_timeline(client, db_session) -> None:
    db_session.add(Project(project_key='project-alpha', name='Project Alpha', summary='Redis work'))
    item = ReviewItem(
        item_type='todo',
        payload={
            'title': 'Redis 큐 점검',
            'priority': 'high',
            'priority_reason': 'Redis 큐 상태를 확인해야 합니다.',
            'agent_name': 'slack_agent',
            'project_assignment_method': 'llm_tool',
            'project_key': 'project-alpha',
            'project_name': 'Project Alpha',
        },
        source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
        source_snippets=['Redis 큐 상태 확인 필요'],
        confidence_score=0.9,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    approve = client.post(f'/api/v1/review/{item.id}/approve')
    projects = client.get('/api/v1/projects').json()['projects']
    project = next(project for project in projects if project['project_key'] == 'project-alpha')

    assert approve.status_code == 200
    assert any(activity['item_type'] == 'todo' for activity in project['activity_items'])
    assert any(timeline['item_type'] == 'timeline_event' for timeline in project['timeline_items'])
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py::test_slack_tool_routed_approved_items_appear_in_project_activity_and_timeline -q
```

Expected: 현재 구현이 이미 통과할 수도 있다. 통과하면 이 테스트는 회귀 고정으로 유지하고 다음 단계로 진행한다.

- [ ] **Step 3: pending count 보강**

`backend/app/projects/service.py`의 `_pending_assignment_counts()`를 project_assignment 전용에서 모든 pending project-routed Slack Agent 후보로 확장한다.

```python
select(ReviewItem).where(ReviewItem.status == 'pending_review')
```

count 조건:

```python
project_key = item.payload.get('project_key')
if isinstance(project_key, str) and project_key:
    counts[project_key] = counts.get(project_key, 0) + 1
```

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py -q
```

Expected: 관련 Project/Review tests pass.

---

## Task 7: Timeline 날짜 단위 그룹 표시

**Files:**
- Modify: `frontend/src/app/timeline/page.tsx`
- Test: `frontend/e2e/timeline-project-date-groups.spec.ts`

- [ ] **Step 1: Playwright failing test 작성**

`frontend/e2e/timeline-project-date-groups.spec.ts`를 만든다.

```ts
import { expect, test } from "@playwright/test";

test("Timeline groups approved project items by date", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ contentType: "application/json", json: { user: { id: "demo-admin", email: "admin@paraworks.com", role: "admin", permission_levels: ["public", "internal"], name: "Admin", title: "Admin", department: "Platform" } } }));
  await page.route("**/api/v1/notifications", route => route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } }));
  await page.route("**/api/v1/projects", route => route.fulfill({
    contentType: "application/json",
    json: {
      project_count: 1,
      hidden_project_count: 0,
      hidden_evidence_count: 0,
      projects: [{
        project_key: "project-alpha",
        name: "Project Alpha",
        summary: "Redis work",
        source_types: ["slack"],
        evidence_count: 0,
        permission_level: "internal",
        latest_timestamp: "2026-05-15T02:00:00Z",
        pending_review_count: 0,
        evidence: [],
        activity_items: [],
        timeline_items: [
          { id: "timeline_event:1", item_type: "timeline_event", title: "오전 점검", summary: "Redis 점검", source_links: ["https://slack.example/1"], source_snippets: ["점검"], confidence_score: 0.9, permission_level: "internal", review_status: "approved", created_at: "2026-05-15T01:00:00Z", evidence_reason: "승인된 항목", project_key: "project-alpha" },
          { id: "timeline_event:2", item_type: "timeline_event", title: "오후 배포", summary: "배포 완료", source_links: ["https://slack.example/2"], source_snippets: ["배포"], confidence_score: 0.9, permission_level: "internal", review_status: "approved", created_at: "2026-05-15T06:00:00Z", evidence_reason: "승인된 항목", project_key: "project-alpha" },
          { id: "timeline_event:3", item_type: "timeline_event", title: "전날 회의", summary: "회의 완료", source_links: ["https://slack.example/3"], source_snippets: ["회의"], confidence_score: 0.9, permission_level: "internal", review_status: "approved", created_at: "2026-05-14T06:00:00Z", evidence_reason: "승인된 항목", project_key: "project-alpha" },
        ],
      }],
    },
  }));
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/timeline");

  await expect(page.getByText("2026년 5월 15일")).toBeVisible();
  await expect(page.getByText("2026년 5월 14일")).toBeVisible();
  await expect(page.getByText("오전 점검")).toBeVisible();
  await expect(page.getByText("오후 배포")).toBeVisible();
  await expect(page.getByText("전날 회의")).toBeVisible();
});
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts --project=chromium-desktop
```

Expected: 현재 날짜 그룹 헤더가 없어 실패한다.

- [ ] **Step 3: 최소 구현**

`frontend/src/app/timeline/page.tsx`에 group helper를 추가한다.

```ts
function groupHistoriesByDate(histories: TimelineHistory[]) {
  const groups = new Map<string, TimelineHistory[]>();
  for (const history of histories) {
    const label = formatDate(history.createdAt);
    groups.set(label, [...(groups.get(label) ?? []), history]);
  }
  return Array.from(groups.entries()).map(([dateLabel, items]) => ({ dateLabel, items }));
}
```

`TimelineHistory`에 `createdAt: string`을 추가하고, 렌더링을 날짜 그룹 단위로 바꾼다.

```tsx
{groupHistoriesByDate(selectedProject.histories).map((group) => (
  <section key={group.dateLabel} className="space-y-3">
    <h3 className="text-[13px] font-extrabold text-muted">{group.dateLabel}</h3>
    {group.items.map((item) => <TimelineCard key={item.id} item={item} />)}
  </section>
))}
```

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts
```

Expected: desktop/mobile `2 passed`.

---

## Task 8: Project 탭 metric 겹침 방지

**Files:**
- Modify: `frontend/src/app/projects/page.tsx`
- Test: `frontend/e2e/projects-responsive-metrics.spec.ts`

- [ ] **Step 1: Playwright failing test 작성**

`frontend/e2e/projects-responsive-metrics.spec.ts`를 만든다.

```ts
import { expect, test } from "@playwright/test";

test("Project metrics do not overlap on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/auth/me", route => route.fulfill({ contentType: "application/json", json: { user: { id: "demo-admin", email: "admin@paraworks.com", role: "admin", permission_levels: ["public", "internal"], name: "Admin", title: "Admin", department: "Platform" } } }));
  await page.route("**/api/v1/notifications", route => route.fulfill({ contentType: "application/json", json: { unread_count: 0, notifications: [] } }));
  await page.route("**/api/v1/projects", route => route.fulfill({ contentType: "application/json", json: { project_count: 1, hidden_project_count: 0, hidden_evidence_count: 0, projects: [{ project_key: "project-alpha", name: "아주 긴 프로젝트 이름으로 레이아웃 확인", summary: "모바일 겹침 확인", source_types: ["slack"], evidence_count: 1234, permission_level: "internal", latest_timestamp: "2026-05-15T02:00:00Z", pending_review_count: 987, evidence: [], activity_items: [{ id: "todo:1", item_type: "todo", title: "활동", summary: "활동", source_links: [], source_snippets: [], confidence_score: 0.9, permission_level: "internal", review_status: "approved", created_at: "2026-05-15T02:00:00Z", evidence_reason: "근거", project_key: "project-alpha" }], timeline_items: [] }] } }));
  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));

  await page.goto("/projects");

  const metrics = page.locator('[data-testid="project-metric"]');
  await expect(metrics).toHaveCount(3);
  for (let index = 0; index < 3; index += 1) {
    await expect(metrics.nth(index)).toBeVisible();
  }
});
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
npm.cmd run test:visual -- projects-responsive-metrics.spec.ts --project=chromium-mobile
```

Expected: 현재 test id가 없어 실패한다. 레이아웃 겹침이 있으면 screenshot도 실패 근거가 된다.

- [ ] **Step 3: 최소 구현**

`frontend/src/app/projects/page.tsx` metric grid를 바꾼다.

```tsx
<div className="grid w-full grid-cols-1 gap-2 text-center sm:w-auto sm:grid-cols-3">
```

`Metric`에 test id와 overflow-safe class를 추가한다.

```tsx
<div data-testid="project-metric" className="min-w-0 rounded-lg border border-line bg-white px-3 py-2">
```

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
npm.cmd run test:visual -- projects-responsive-metrics.spec.ts
```

Expected: desktop/mobile `2 passed`.

---

## Task 9: 통합 Playwright 시나리오

**Files:**
- Test: `frontend/e2e/slack-project-routing-flow.spec.ts`

- [ ] **Step 1: mocked E2E 작성**

이 테스트는 live Slack/LLM을 호출하지 않는다. 브라우저 흐름은 실제 페이지를 통과하되 API는 route mock으로 제어한다.

시나리오:

1. `/integrations`에서 Slack sync 클릭
2. sync modal이 완료 상태 표시
3. `/review`로 이동
4. 첫 번째 Slack Agent 후보는 Project Alpha가 이미 선택되어 있고 승인 가능
5. 두 번째 후보는 프로젝트 미선택이라 승인 불가
6. 사용자가 Project Alpha를 선택하면 PATCH mock이 payload에 project_key/project_name을 채운 응답 반환
7. promotion preview mock이 can_approve true로 바뀜
8. 승인 mock 후 `/timeline`에서 날짜 그룹과 승인 항목 표시
9. `/projects`에서 활동 count와 활동 카드 표시

테스트 파일 이름:

```powershell
frontend/e2e/slack-project-routing-flow.spec.ts
```

- [ ] **Step 2: 실행**

Run:

```powershell
npm.cmd run test:visual -- slack-project-routing-flow.spec.ts --project=chromium-desktop
npm.cmd run test:visual -- slack-project-routing-flow.spec.ts --project=chromium-mobile
```

Expected: desktop/mobile 모두 통과.

---

## Task 10: 전체 검증 묶음

**Files:**
- Docs: `agent_slack/20260514_project_timeline_rag_progress.md`
- Docs: `docs/portfolio-log.md`
- Docs: `docs/superpowers/runbooks/session-handoff.md`

- [ ] **Step 1: backend targeted tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_project_routing.py backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q
```

Expected: all passed.

- [ ] **Step 2: ruff**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run ruff check agent_slack/project_routing.py agent_slack/agent_slack.py backend/app/agents/slack_agent/sync_service.py backend/app/api/v1/integrations.py backend/app/api/v1/projects.py backend/app/projects/classifier.py backend/app/knowledge/promotion.py backend/app/projects/service.py backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py backend/tests/test_project_memory_api.py backend/tests/test_review.py
```

Expected: all checks passed.

- [ ] **Step 3: frontend static checks**

Run:

```powershell
npm.cmd exec tsc -- --noEmit
npm.cmd run lint
npm.cmd run build
```

Expected: all passed.

- [ ] **Step 4: Playwright**

Run:

```powershell
npm.cmd run test:visual -- review-project-routing-required.spec.ts
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts
npm.cmd run test:visual -- projects-responsive-metrics.spec.ts
npm.cmd run test:visual -- slack-project-routing-flow.spec.ts
```

Expected: desktop/mobile all passed.

- [ ] **Step 5: 문서 갱신**

`agent_slack/20260514_project_timeline_rag_progress.md`에 작업 완료 순서대로 다음 내용을 추가한다.

```markdown
## 2026-05-15 Slack 프로젝트 Tool Routing 통합 완료

- 신규 Slack sync에서 규칙 기반 `project_assignment` 생성을 중단했다.
- Slack Agent 후보는 LangChain tool routing 결과만 프로젝트 지정 근거로 사용한다.
- 프로젝트 미선택 Slack Agent 후보는 Review에서 승인할 수 없고, 사용자가 프로젝트를 선택하거나 새 프로젝트를 만든 뒤 승인해야 한다.
- 승인된 항목은 프로젝트 `project_key`로 TimelineEvent/DecisionRecord/HistoryEvent/Todo에 저장되어 타임라인과 프로젝트 탭에 반영된다.
- Playwright로 Review 선택 필요, Timeline 날짜 그룹, Project metric 모바일 레이아웃, 통합 flow를 검증했다.
```

`docs/portfolio-log.md`와 `docs/superpowers/runbooks/session-handoff.md`도 같은 요지를 한국어로 업데이트한다.

---

## Playwright 테스트 전략

- **mocked UI regression:** 빠르고 안정적인 검증. API route mock으로 정확한 프로젝트 라우팅 상태를 만들어 Review/Timeline/Projects UI를 확인한다.
- **browser flow regression:** `/integrations -> /review -> /timeline -> /projects` 전체 화면 이동을 검증한다. live Slack/LLM은 호출하지 않고, route mock으로 long-running sync와 승인 결과를 통제한다.
- **mobile layout regression:** `chromium-mobile`에서 Review select, Timeline date group, Project metric 영역이 겹치지 않는지 확인한다.
- **actual local smoke:** 구현 후 사용자가 서버를 띄운 상태에서 별도 확인이 필요하면 Playwright로 실제 `/integrations` Slack sync 버튼을 클릭하되, live Slack/LLM 결과 수는 DB 상태와 provider key에 따라 달라지므로 pass/fail 기준은 “UI가 실패로 오인하지 않고 Review API와 count가 일치하는지”로 둔다.

## 자체 검토

- 요구사항 1, 2: Slack sync와 업무용 판단은 기존 경로를 유지하고, 저신호 필터는 건드리지 않는다.
- 요구사항 3: 등록 프로젝트 판단은 `project_route` LangChain tool node에서 수행한다.
- 요구사항 4: tool이 확정한 프로젝트는 Review의 프로젝트 지정 select 기본값으로 들어간다.
- 요구사항 5: tool이 확정하지 못하면 프로젝트 미선택 상태로 표시하고 승인 불가로 만든다. 새 프로젝트 생성 링크를 제공한다.
- 요구사항 6: 승인 후 `project_key`가 trusted knowledge와 `TimelineEvent`에 저장되어 타임라인/프로젝트 탭에 반영된다. 타임라인 날짜 그룹과 프로젝트 metric 겹침도 포함했다.
- 테스트 계획: backend TDD, Playwright desktop/mobile, 통합 browser flow까지 포함했다.
