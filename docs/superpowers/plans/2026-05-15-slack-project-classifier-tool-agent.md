# Slack 프로젝트 분류 Tool Agent 구현 계획서

> **작업자 안내:** 이 계획을 구현할 때는 `superpowers:subagent-driven-development`(권장) 또는 `superpowers:executing-plans`를 사용해 작업 단위로 진행한다. 각 단계는 체크박스(`- [ ]`)로 상태를 추적한다.

**목표:** 기존 `agent_slack` LangGraph 흐름 안에 LangChain tool-calling 기반 프로젝트 분류 Agent를 추가해, Slack 지식 후보가 등록된 프로젝트 중 어디에 속하는지 LLM이 근거와 요약을 포함해 제안하도록 만든다.

**구조:** Slack Agent는 지금처럼 업무 신호 필터링, 요약, 지식 후보 추출을 수행한다. 그 다음 새 `project_route` 노드가 LangChain `create_agent`와 project tools를 사용해 등록 프로젝트 목록 조회, 규칙 기반 후보 점수 확인, 최종 프로젝트 선택/요약을 수행한다. LLM 결과는 바로 trusted knowledge가 아니라 `ReviewItem(status='pending_review')` payload와 evidence에 보존되고, 사용자가 Review 화면에서 프로젝트를 바꾸거나 승인해야 프로젝트 활동으로 확정된다.

**기술 스택:** Python 3.12, FastAPI, SQLAlchemy, LangChain 1.x `create_agent`, LangGraph `StateGraph`, Pydantic v2, pytest, Next.js/React/TypeScript, Playwright.

**실행 상태:** 2026-05-15 구현 완료.

**검증 결과:** 관련 백엔드 회귀 테스트 `60 passed`, ruff 통과, 프론트엔드 TypeScript/lint/build 통과, Playwright `review-project-routing.spec.ts` desktop/mobile `2 passed`.

**LangGraph 문서:** `agent_slack/slack_agent_langgraph.md`.

---

## 참고 문서

- LangChain 공식 문서: agents는 model과 tools를 사용해 반복적으로 tool call을 수행하는 시스템이며 `create_agent`로 생성한다. https://docs.langchain.com/oss/python/langchain/agents
- LangChain 공식 문서: tools는 `@tool` 데코레이터 또는 callable로 정의하고 agent에 전달한다. https://docs.langchain.com/oss/python/langchain/tools
- 현재 제품 방향: `plan.md`의 Evidence first, Review Queue boundary, Cost-aware, Permission-safe 원칙을 유지한다.

---

## 현재 상태 요약

- `agent_slack/agent_slack.py`는 `StateGraph`로 `preprocess -> classify -> summarize -> extract` 노드를 실행한다.
- `extract_candidate_node()`는 LLM structured output으로 `decision_record`, `todo`, `history_event` 후보를 만든다.
- `backend/app/agents/slack_agent/sync_service.py`는 `process_daily_slack_sync()` 결과를 `AgentRun`과 `ReviewItem`으로 저장한다.
- 현재 `project_assignment`는 `backend/app/projects/classifier.py`의 `create_project_assignment_review_items()`가 규칙 기반으로 생성한다.
- Review UI는 `project_classifier` 항목을 `규칙 기반 분류`, `LLM 미사용`으로 표시한다.
- 문제: 프로젝트 분류와 프로젝트별 요약은 LLM이 수행하지 않으며, 현재 summary는 source snippet을 자르는 수준이다.

---

## 목표 동작

1. Slack LLM Agent가 후보를 추출한 뒤 등록 프로젝트 목록을 tool로 조회한다.
2. Agent는 evidence와 후보 summary를 보고 프로젝트를 하나 선택하거나 `needs_user_selection`으로 표시한다.
3. Agent는 프로젝트 연결 요약, 연결 근거, 확신도, 대체 후보를 생성한다.
4. ReviewItem에는 다음 필드가 들어간다.
   - `project_key`
   - `project_name`
   - `project_assignment_method: "llm_tool"`
   - `project_assignment_summary`
   - `project_assignment_reason`
   - `project_assignment_confidence`
   - `project_alternatives`
   - `project_needs_user_selection`
5. Review 화면은 해당 항목을 `LLM 프로젝트 분류`로 표시한다.
6. 사용자는 Review 화면에서 프로젝트를 직접 바꿀 수 있고, 승인 시 선택한 프로젝트로 trusted knowledge가 승격된다.
7. Slack LLM project routing이 실행된 경우 같은 Slack source에 대해 기존 규칙 기반 `project_assignment`가 중복 생성되지 않는다.
8. provider key가 없거나 LLM이 비활성화된 경우 기존 규칙 기반 분류는 fallback으로 유지한다.

---

## 파일 구조

- 생성: `agent_slack/project_routing.py`
  - 프로젝트 라우팅용 Pydantic 모델, tool factory, deterministic project scoring, LangChain project router runner를 둔다.
- 수정: `agent_slack/agent_slack.py`
  - `SlackAgentState`에 `projects`, `project_assignments`, `project_prompt_tokens`, `project_completion_tokens`를 추가한다.
  - `project_route_node`를 추가하고 `extract -> project_route -> END`로 연결한다.
  - `process_daily_slack_sync()`가 `projects` 인자를 받게 한다.
- 수정: `backend/app/agents/slack_agent/sync_service.py`
  - DB의 등록 프로젝트를 `agent_slack`에 전달한다.
  - project routing 결과를 `ReviewItem.payload`와 `AgentRun.metadata_`에 저장한다.
- 수정: `backend/app/api/v1/integrations.py`
  - Slack LLM project routing이 실행된 경우 기존 deterministic `create_project_assignment_review_items()` 호출을 건너뛰거나 Slack source를 제외한다.
- 수정: `backend/app/projects/classifier.py`
  - fallback deterministic classifier는 유지하되, connector/source type 제한 인자를 받을 수 있게 한다.
- 수정: `frontend/src/app/review/page.tsx`
  - `project_assignment_method === "llm_tool"`이면 Prompt/Cost 영역에 `LLM 프로젝트 분류`를 표시한다.
  - 프로젝트 연결 요약/근거를 카드에서 보이게 한다.
- 수정: `frontend/src/lib/api/types.ts`
  - Review payload helper에서 새 project assignment metadata를 안전하게 읽을 수 있게 한다.
- 테스트: `backend/tests/test_agent_slack_project_routing.py`
- 테스트: `backend/tests/test_slack_agent_api.py`
- 테스트: `backend/tests/test_mock_sync.py`
- 테스트: `backend/tests/test_project_memory_api.py`
- 테스트: `frontend/e2e/review-project-routing.spec.ts`
- 문서: `agent_slack/20260514_project_timeline_rag_progress.md`, `docs/portfolio-log.md`, `docs/superpowers/runbooks/session-handoff.md`

---

## 데이터 계약

### 프로젝트 옵션 모델(`ProjectOption`)

```python
class ProjectOption(BaseModel):
    project_key: str
    name: str
    summary: str
```

### 프로젝트 분류 결정 모델(`ProjectRoutingDecision`)

```python
class ProjectRoutingDecision(BaseModel):
    source_id: str
    item_index: int
    project_key: str | None
    project_name: str | None
    confidence_score: float
    assignment_summary: str
    assignment_reason: str
    alternatives: list[str] = Field(default_factory=list)
    needs_user_selection: bool = False
```

### 검토 항목 페이로드 추가 필드

```python
{
    "project_key": "project-alpha",
    "project_name": "Project Alpha",
    "project_assignment_method": "llm_tool",
    "project_assignment_summary": "Redis 큐 상태 확인과 백엔드 처리 흐름 개선 논의입니다.",
    "project_assignment_reason": "근거 메시지에서 Redis, queue, sync job 상태를 함께 다뤘고 Project Alpha 설명과 일치합니다.",
    "project_assignment_confidence": 0.84,
    "project_alternatives": ["project-beta"],
    "project_needs_user_selection": False
}
```

---

## 작업 1: 프로젝트 분류 계약과 Tool 단위 테스트 추가

**대상 파일:**
- 생성: `agent_slack/project_routing.py`
- 생성: `backend/tests/test_agent_slack_project_routing.py`

- [ ] **단계 1: 실패 테스트를 작성한다**

`backend/tests/test_agent_slack_project_routing.py`를 만든다.

```python
from agent_slack.project_routing import (
    ProjectOption,
    build_project_tools,
    score_project_aliases,
)


def test_project_alias_tool_ranks_registered_project() -> None:
    projects = [
        ProjectOption(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        ),
        ProjectOption(
            project_key='project-kindergarten',
            name='유치원 등교',
            summary='개인 일정과 등교 안내',
        ),
    ]

    ranked = score_project_aliases(
        text='Redis queue 상태와 sync job 실패 복구 흐름을 논의했습니다.',
        projects=projects,
    )

    assert ranked[0]['project_key'] == 'project-alpha'
    assert ranked[0]['score'] > ranked[1]['score']


def test_project_tools_expose_registered_projects_as_json() -> None:
    projects = [
        ProjectOption(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        )
    ]

    tools = build_project_tools(projects)
    tool_by_name = {tool.name: tool for tool in tools}

    assert 'list_registered_projects' in tool_by_name
    assert 'score_project_candidates' in tool_by_name
    assert 'project-alpha' in tool_by_name['list_registered_projects'].invoke({})
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_project_routing.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'agent_slack.project_routing'
```

- [ ] **단계 3: 최소 구현을 추가한다**

`agent_slack/project_routing.py`를 만든다.

```python
import json
import re
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ProjectOption(BaseModel):
    project_key: str
    name: str
    summary: str


class ProjectRoutingDecision(BaseModel):
    source_id: str
    item_index: int
    project_key: str | None = None
    project_name: str | None = None
    confidence_score: float = Field(ge=0, le=1)
    assignment_summary: str
    assignment_reason: str
    alternatives: list[str] = Field(default_factory=list)
    needs_user_selection: bool = False


class ProjectRoutingResult(BaseModel):
    decisions: list[ProjectRoutingDecision] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str = 'deterministic-project-router'


def score_project_aliases(text: str, projects: list[ProjectOption]) -> list[dict[str, Any]]:
    normalized = _normalize(text)
    ranked: list[dict[str, Any]] = []
    for project in projects:
        terms = _project_terms(project)
        hits = [term for term in terms if _contains_term(normalized, term)]
        score = min(1.0, len(hits) / max(2, len(terms)))
        ranked.append(
            {
                'project_key': project.project_key,
                'name': project.name,
                'score': round(score, 4),
                'matched_terms': hits[:8],
            }
        )
    return sorted(ranked, key=lambda item: item['score'], reverse=True)


def build_project_tools(projects: list[ProjectOption]):
    @tool
    def list_registered_projects() -> str:
        """Return registered ParaWorks projects as JSON."""
        return json.dumps([project.model_dump() for project in projects], ensure_ascii=False)

    @tool
    def score_project_candidates(text: str) -> str:
        """Return deterministic project candidate scores for the given evidence text."""
        return json.dumps(score_project_aliases(text, projects), ensure_ascii=False)

    return [list_registered_projects, score_project_candidates]


def _project_terms(project: ProjectOption) -> list[str]:
    raw = f'{project.project_key} {project.name} {project.summary}'
    terms = re.findall(r'[0-9A-Za-z가-힣]{2,}', raw.lower())
    stopwords = {'project', 'slack', 'gmail', 'drive', 'data', 'timeline', '프로젝트', '업무', '진행'}
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        if term in stopwords or term in seen:
            continue
        seen.add(term)
        result.append(term)
    return result


def _normalize(text: str) -> str:
    return ' '.join(text.lower().split())


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf'(?<![0-9a-z가-힣]){re.escape(term)}(?![0-9a-z가-힣])', text) is not None
```

- [ ] **단계 4: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_project_routing.py -q
```

Expected:

```text
2 passed
```

---

## 작업 2: LangChain Tool-Calling 프로젝트 Router 추가

**대상 파일:**
- 수정: `agent_slack/project_routing.py`
- 테스트: `backend/tests/test_agent_slack_project_routing.py`

- [ ] **단계 1: fake tool-calling runner 테스트를 추가한다**

같은 테스트 파일에 아래 테스트를 추가한다. live LLM을 호출하지 않는다.

```python
from agent_slack.project_routing import route_projects_for_candidates


class FakeProjectRouterModel:
    model_name = 'fake-project-router'

    def invoke(self, payload):
        return {
            'decisions': [
                {
                    'source_id': 'C123:1777600800.000100',
                    'item_index': 0,
                    'project_key': 'project-alpha',
                    'project_name': 'Project Alpha',
                    'confidence_score': 0.86,
                    'assignment_summary': 'Redis 큐 상태와 동기화 안정성 개선 논의입니다.',
                    'assignment_reason': 'Redis, queue, sync job이 프로젝트 설명과 직접 일치합니다.',
                    'alternatives': [],
                    'needs_user_selection': False,
                }
            ],
            'input_tokens': 100,
            'output_tokens': 40,
            'model_name': 'fake-project-router',
        }


def test_route_projects_for_candidates_returns_llm_tool_decision() -> None:
    result = route_projects_for_candidates(
        model=FakeProjectRouterModel(),
        projects=[
            ProjectOption(
                project_key='project-alpha',
                name='Project Alpha',
                summary='Redis queue status and sync job reliability work',
            )
        ],
        candidates=[
            {
                'item_index': 0,
                'source_id': 'C123:1777600800.000100',
                'title': 'Redis 큐 상태 확인',
                'summary': 'Redis 큐와 동기화 작업 상태를 확인했습니다.',
                'source_snippets': ['Redis queue 상태를 확인하고 sync job을 복구합니다.'],
            }
        ],
    )

    assert result.decisions[0].project_key == 'project-alpha'
    assert result.decisions[0].assignment_summary
    assert result.input_tokens == 100
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_project_routing.py::test_route_projects_for_candidates_returns_llm_tool_decision -q
```

Expected:

```text
ImportError: cannot import name 'route_projects_for_candidates'
```

- [ ] **단계 3: router 함수를 구현한다**

`agent_slack/project_routing.py`에 추가한다.

```python
def route_projects_for_candidates(
    *,
    model: Any,
    projects: list[ProjectOption],
    candidates: list[dict[str, Any]],
) -> ProjectRoutingResult:
    if not projects or not candidates:
        return ProjectRoutingResult(decisions=[])

    payload = {
        'task': (
            '등록 프로젝트 중 Slack 후보가 어느 프로젝트에 속하는지 고르고, '
            '프로젝트 활동 요약과 근거를 한국어로 작성하세요.'
        ),
        'rules': [
            '반드시 list_registered_projects tool로 프로젝트 목록을 확인하세요.',
            '프로젝트가 애매하면 score_project_candidates tool 결과를 참고하세요.',
            '근거가 부족하면 project_key를 null로 두고 needs_user_selection=true로 두세요.',
            '새 프로젝트를 만들지 마세요. 등록된 프로젝트 중에서만 선택하세요.',
        ],
        'projects_count': len(projects),
        'candidate_items': candidates,
    }

    raw_result = model.invoke(payload)
    if isinstance(raw_result, ProjectRoutingResult):
        return raw_result
    if isinstance(raw_result, dict):
        return ProjectRoutingResult.model_validate(raw_result)
    return ProjectRoutingResult.model_validate_json(str(raw_result))
```

- [ ] **단계 4: LangChain `create_agent` 래퍼를 추가한다**

`agent_slack/project_routing.py`에 추가한다. 이 함수는 실제 provider가 있을 때만 사용한다.

```python
class LangChainProjectRouterModel:
    def __init__(self, *, chat_model: Any, projects: list[ProjectOption], model_name: str) -> None:
        from langchain.agents import create_agent

        self.model_name = model_name
        self.agent = create_agent(
            model=chat_model,
            tools=build_project_tools(projects),
            response_format=ProjectRoutingResult,
            system_prompt=(
                '당신은 ParaWorks Slack 프로젝트 분류 Router입니다. '
                '결정하기 전에 반드시 tool을 사용하고, 한국어 요약과 근거 기반 사유만 반환하세요.'
            ),
        )

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.agent.invoke(
            {
                'messages': [
                    {
                        'role': 'user',
                        'content': json.dumps(payload, ensure_ascii=False),
                    }
                ]
            }
        )
        structured = response.get('structured_response')
        if isinstance(structured, ProjectRoutingResult):
            return structured.model_dump()
        return ProjectRoutingResult.model_validate(structured).model_dump()
```

- [ ] **단계 5: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_project_routing.py -q
```

Expected:

```text
3 passed
```

---

## 작업 3: `agent_slack` 그래프에 `project_route` 노드 연결

**대상 파일:**
- 수정: `agent_slack/agent_slack.py`
- 테스트: `backend/tests/test_agent_slack_pipeline_quality.py`

- [ ] **단계 1: graph routing 테스트를 추가한다**

`backend/tests/test_agent_slack_pipeline_quality.py`에 추가한다.

```python
from agent_slack.project_routing import ProjectRoutingResult, ProjectRoutingDecision, ProjectOption


def test_agent_slack_applies_project_routing_to_candidates(monkeypatch) -> None:
    def fake_route_projects_for_candidates(*, model, projects, candidates):
        return ProjectRoutingResult(
            decisions=[
                ProjectRoutingDecision(
                    source_id='C123:1777600800.000100',
                    item_index=0,
                    project_key='project-alpha',
                    project_name='Project Alpha',
                    confidence_score=0.86,
                    assignment_summary='Redis 큐 상태와 동기화 안정성 개선 논의입니다.',
                    assignment_reason='Redis와 sync job 근거가 Project Alpha와 일치합니다.',
                )
            ],
            input_tokens=10,
            output_tokens=5,
            model_name='fake-project-router',
        )

    monkeypatch.setattr(agent_module, 'route_projects_for_candidates', fake_route_projects_for_candidates)

    state = agent_module.SlackAgentState(
        channel_id='C123',
        candidates=[
            agent_module.ReviewCandidate(
                item_type='history_event',
                title='Redis 큐 상태 확인',
                summary='Redis 큐와 동기화 작업 상태를 확인했습니다.',
                source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
                source_snippets=['Redis queue 상태를 확인하고 sync job을 복구합니다.'],
                confidence_score=0.9,
                permission_level='internal',
                payload_fields={},
            )
        ],
        projects=[
            ProjectOption(
                project_key='project-alpha',
                name='Project Alpha',
                summary='Redis queue status and sync job reliability work',
            )
        ],
    )

    result = agent_module.project_route_node(state)

    routed = result['candidates'][0]
    assert routed.payload_fields['project_key'] == 'project-alpha'
    assert routed.payload_fields['project_assignment_method'] == 'llm_tool'
    assert result['total_prompt_tokens'] == 10
    assert result['total_completion_tokens'] == 5
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_pipeline_quality.py::test_agent_slack_applies_project_routing_to_candidates -q
```

Expected:

```text
AttributeError: module 'agent_slack.agent_slack' has no attribute 'project_route_node'
```

- [ ] **단계 3: State와 import를 추가한다**

`agent_slack/agent_slack.py` 상단 import에 추가한다.

```python
from agent_slack.project_routing import (
    LangChainProjectRouterModel,
    ProjectOption,
    route_projects_for_candidates,
)
```

`SlackAgentState`에 필드를 추가한다.

```python
projects: list[ProjectOption] = Field(default_factory=list)
project_router_model_name: str = 'gpt-5-mini'
```

- [ ] **단계 4: `project_route_node`를 추가한다**

`extract_candidate_node` 아래에 추가한다.

```python
def project_route_node(state: SlackAgentState):
    if not state.candidates or not state.projects:
        return {'candidates': state.candidates}

    candidate_payloads = []
    for index, candidate in enumerate(state.candidates):
        source_id = _source_id_from_link(candidate.source_links[0], state.channel_id) if candidate.source_links else ''
        candidate_payloads.append(
            {
                'item_index': index,
                'source_id': source_id,
                'title': candidate.title,
                'summary': candidate.summary,
                'source_snippets': candidate.source_snippets,
            }
        )

    model = _build_project_router_model(state)
    result = route_projects_for_candidates(
        model=model,
        projects=state.projects,
        candidates=candidate_payloads,
    )

    candidates = list(state.candidates)
    for decision in result.decisions:
        if decision.item_index < 0 or decision.item_index >= len(candidates):
            continue
        candidate = candidates[decision.item_index]
        fields = dict(candidate.payload_fields)
        fields.update(
            {
                'project_key': decision.project_key,
                'project_name': decision.project_name,
                'project_assignment_method': 'llm_tool',
                'project_assignment_summary': decision.assignment_summary,
                'project_assignment_reason': decision.assignment_reason,
                'project_assignment_confidence': decision.confidence_score,
                'project_alternatives': decision.alternatives,
                'project_needs_user_selection': decision.needs_user_selection,
            }
        )
        candidates[decision.item_index] = candidate.model_copy(update={'payload_fields': fields})

    return {
        'candidates': candidates,
        'model_name': result.model_name or state.model_name,
        'total_prompt_tokens': state.total_prompt_tokens + result.input_tokens,
        'total_completion_tokens': state.total_completion_tokens + result.output_tokens,
    }
```

같은 파일에 helper를 추가한다.

```python
def _source_id_from_link(source_link: str, channel_id: str) -> str:
    if '/p' not in source_link:
        return ''
    raw_ts = source_link.split('/p')[-1].split('?')[0]
    if len(raw_ts) < 16:
        return ''
    return f'{channel_id}:{raw_ts[:10]}.{raw_ts[10:]}'


def _build_project_router_model(state: SlackAgentState):
    llm = ChatOpenAI(
        model=state.project_router_model_name,
        temperature=0,
        api_key=state.openai_api_key,
    )
    return LangChainProjectRouterModel(
        chat_model=llm,
        projects=state.projects,
        model_name=state.project_router_model_name,
    )
```

- [ ] **단계 5: Graph edge를 변경한다**

`build_slack_agent_graph()`에서 노드와 edge를 추가한다.

```python
workflow.add_node("project_route", project_route_node)
workflow.add_edge("summarize", "extract")
workflow.add_edge("extract", "project_route")
workflow.add_edge("project_route", END)
```

기존 `workflow.add_edge("extract", END)`는 제거한다.

- [ ] **단계 6: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_pipeline_quality.py -q
```

Expected:

```text
2 passed
```

---

## 작업 4: DB 등록 프로젝트를 `agent_slack`에 전달

**대상 파일:**
- 수정: `backend/app/agents/slack_agent/sync_service.py`
- 테스트: `backend/tests/test_slack_agent_api.py`

- [ ] **단계 1: 프로젝트 전달 테스트를 추가한다**

`backend/tests/test_slack_agent_api.py`에 추가한다.

```python
from backend.app.models import Project


def test_slack_sync_passes_registered_projects_to_agent_slack(
    client,
    db_session: Session,
    monkeypatch,
) -> None:
    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        )
    )
    db_session.commit()

    def override_settings() -> Settings:
        return Settings(paraworks_demo_mode=False, openai_api_key='openai-key')

    observed_projects: list[list[dict[str, str]]] = []

    def fake_process_daily_slack_sync(
        channel_id: str,
        messages: list[dict],
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
        projects: list[dict[str, str]] | None = None,
    ) -> dict:
        observed_projects.append(projects or [])
        return {
            'model_name': 'gpt-5-mini',
            'is_work_related': True,
            'run_cost': AgentRunCost(
                model_name='gpt-5-mini',
                token_usage=TokenUsage(input_tokens=120, output_tokens=40),
                estimated_cost_usd=0.000042,
                cache_hit=False,
            ),
            'candidates': [],
        }

    client.app.dependency_overrides[get_settings] = override_settings
    monkeypatch.setattr(
        'backend.app.api.v1.integrations.get_sync_connector',
        lambda *args, **kwargs: get_mock_connector('slack'),
    )
    monkeypatch.setattr(sync_service, 'process_daily_slack_sync', fake_process_daily_slack_sync)

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert observed_projects
    assert observed_projects[0][0]['project_key'] == 'project-alpha'
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_api.py::test_slack_sync_passes_registered_projects_to_agent_slack -q
```

Expected:

```text
TypeError 또는 AssertionError: projects가 전달되지 않음
```

- [ ] **단계 3: 프로젝트 serializer를 추가한다**

`backend/app/agents/slack_agent/sync_service.py`에 import와 helper를 추가한다.

```python
from backend.app.models import Project


def _registered_project_options(db: Session) -> list[dict[str, str]]:
    projects = db.scalars(select(Project).order_by(Project.created_at.desc(), Project.id.desc())).all()
    return [
        {
            'project_key': project.project_key,
            'name': project.name,
            'summary': project.summary,
        }
        for project in projects
    ]
```

- [ ] **단계 4: `process_daily_slack_sync()` 호출에 projects를 전달한다**

기존 호출을 바꾼다.

```python
project_options = _registered_project_options(db)

result = process_daily_slack_sync(
    channel_id,
    messages,
    openai_api_key=settings.openai_api_key,
    gemini_api_key=settings.gemini_api_key or settings.google_api_key,
    projects=project_options,
)
```

- [ ] **단계 5: `agent_slack.process_daily_slack_sync()` 시그니처를 확장한다**

`agent_slack/agent_slack.py`에서 시그니처와 초기 state를 바꾼다.

```python
def process_daily_slack_sync(
    channel_id: str,
    messages: list[dict],
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
    projects: list[dict[str, str]] | None = None,
):
    project_options = [ProjectOption.model_validate(project) for project in (projects or [])]
    initial_state = SlackAgentState(
        channel_id=channel_id,
        messages=messages,
        openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key,
        projects=project_options,
    )
```

- [ ] **단계 6: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_api.py::test_slack_sync_passes_registered_projects_to_agent_slack -q
```

Expected:

```text
1 passed
```

---

## 작업 5: LLM 프로젝트 분류 결과를 검토 항목에 보존

**대상 파일:**
- 수정: `backend/app/agents/slack_agent/sync_service.py`
- 테스트: `backend/tests/test_slack_agent_api.py`

- [ ] **단계 1: payload 보존 테스트를 추가한다**

`backend/tests/test_slack_agent_api.py`에 추가한다.

```python
def test_slack_agent_project_routing_metadata_is_persisted(
    client,
    db_session: Session,
    monkeypatch,
) -> None:
    def override_settings() -> Settings:
        return Settings(paraworks_demo_mode=False, openai_api_key='openai-key')

    def fake_process_daily_slack_sync(*args, **kwargs) -> dict:
        return {
            'model_name': 'gpt-5-mini',
            'is_work_related': True,
            'run_cost': AgentRunCost(
                model_name='gpt-5-mini',
                token_usage=TokenUsage(input_tokens=150, output_tokens=60),
                estimated_cost_usd=0.00006,
                cache_hit=False,
            ),
            'candidates': [
                ReviewCandidate(
                    item_type='history_event',
                    title='Redis 큐 상태 확인',
                    summary='Redis 큐와 동기화 작업 상태를 확인했습니다.',
                    source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
                    source_snippets=['Redis queue 상태를 확인하고 sync job을 복구합니다.'],
                    confidence_score=0.91,
                    permission_level='internal',
                    payload_fields={
                        'category': 'Project',
                        'topic_tag': 'Redis',
                        'project_key': 'project-alpha',
                        'project_name': 'Project Alpha',
                        'project_assignment_method': 'llm_tool',
                        'project_assignment_summary': 'Redis 큐 상태와 동기화 안정성 개선 논의입니다.',
                        'project_assignment_reason': 'Redis와 sync job 근거가 Project Alpha와 일치합니다.',
                        'project_assignment_confidence': 0.86,
                        'project_alternatives': [],
                        'project_needs_user_selection': False,
                    },
                )
            ],
        }

    client.app.dependency_overrides[get_settings] = override_settings
    monkeypatch.setattr(
        'backend.app.api.v1.integrations.get_sync_connector',
        lambda *args, **kwargs: get_mock_connector('slack'),
    )
    monkeypatch.setattr(sync_service, 'process_daily_slack_sync', fake_process_daily_slack_sync)

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    review_item = db_session.scalar(select(ReviewItem))
    assert review_item is not None
    assert review_item.payload['project_key'] == 'project-alpha'
    assert review_item.payload['project_assignment_method'] == 'llm_tool'
    assert review_item.payload['project_assignment_summary']
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_project_routing_metadata_is_persisted -q
```

Expected:

```text
KeyError: 'project_assignment_method'
```

- [ ] **단계 3: payload mapping을 확장한다**

`backend/app/agents/slack_agent/sync_service.py`의 payload 생성부에 추가한다.

```python
project_fields = {
    key: candidate.payload_fields.get(key)
    for key in (
        'project_key',
        'project_name',
        'project_assignment_method',
        'project_assignment_summary',
        'project_assignment_reason',
        'project_assignment_confidence',
        'project_alternatives',
        'project_needs_user_selection',
    )
    if key in candidate.payload_fields
}

payload = {
    'title': candidate.title,
    'summary': candidate.summary,
    'category': candidate.payload_fields.get('category', 'Ad-hoc'),
    'topic_tag': topic_tag,
    'importance': candidate.payload_fields.get('importance', 'Medium'),
    'assignee': candidate.payload_fields.get('assignee', '미정'),
    'due_date': candidate.payload_fields.get('due_date', '기한 없음'),
    'project_key': project_fields.get('project_key', project_key),
    'is_new_project': is_new_project,
    'agent_run_id': agent_run.id,
    'agent_name': 'slack_agent',
    'prompt_version': agent_run.prompt_version,
    'estimated_cost_usd': agent_run.estimated_cost_usd,
    'source_ids': source_ids,
    'source_authors': source_authors,
    **project_fields,
}
```

- [ ] **단계 4: AgentRun metadata에 project routing 여부를 기록한다**

`AgentRun.metadata_`에 추가한다.

```python
metadata_={
    'channel_id': channel_id,
    'is_work_related': result.get('is_work_related', False),
    'project_routing': {
        'enabled': bool(project_options),
        'method': 'langchain_tools',
        'project_count': len(project_options),
    },
},
```

- [ ] **단계 5: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_project_routing_metadata_is_persisted -q
```

Expected:

```text
1 passed
```

---

## 작업 6: Slack LLM 프로젝트 분류 시 deterministic project assignment 중복 방지

**대상 파일:**
- 수정: `backend/app/api/v1/integrations.py`
- 수정: `backend/app/projects/classifier.py`
- 테스트: `backend/tests/test_mock_sync.py`

- [ ] **단계 1: 중복 방지 테스트를 추가한다**

`backend/tests/test_mock_sync.py`에 추가한다.

```python
def test_slack_llm_project_routing_skips_deterministic_project_assignments(
    client,
    db_session,
    monkeypatch,
) -> None:
    from backend.app.api.v1 import integrations as integrations_api

    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis queue status and sync job reliability work',
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        integrations_api,
        '_run_connector_agent_review',
        lambda **kwargs: 1,
    )
    monkeypatch.setattr(
        integrations_api,
        '_connector_uses_slack_llm_project_routing',
        lambda *, connector_type, settings: True,
    )

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert response.json()['agent_generated_items'] == 1
    assert response.json()['project_assignment_items'] == 0
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mock_sync.py::test_slack_llm_project_routing_skips_deterministic_project_assignments -q
```

Expected:

```text
AttributeError 또는 AssertionError: project_assignment_items가 0이 아님
```

- [ ] **단계 3: helper를 추가한다**

`backend/app/api/v1/integrations.py`에 추가한다.

```python
def _connector_uses_slack_llm_project_routing(*, connector_type: str, settings: Settings) -> bool:
    return connector_type == 'slack' and not settings.paraworks_demo_mode and bool(
        settings.openai_api_key or settings.gemini_api_key or settings.google_api_key
    )
```

- [ ] **단계 4: project assignment 호출 조건을 변경한다**

`_perform_connector_sync()`에서 두 군데의 `create_project_assignment_review_items(db)` 호출을 다음처럼 감싼다.

```python
if not _connector_uses_slack_llm_project_routing(connector_type=connector_type, settings=settings):
    project_assignment_items = len(create_project_assignment_review_items(db))
```

- [ ] **단계 5: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mock_sync.py::test_slack_llm_project_routing_skips_deterministic_project_assignments -q
```

Expected:

```text
1 passed
```

---

## 작업 7: Review UI에 LLM 프로젝트 분류 정보 표시

**대상 파일:**
- 수정: `frontend/src/app/review/page.tsx`
- 수정: `frontend/src/lib/api/types.ts`
- 테스트: `frontend/e2e/review-project-routing.spec.ts`

- [ ] **단계 1: Playwright 실패 테스트를 추가한다**

`frontend/e2e/review-project-routing.spec.ts`를 만든다.

```typescript
import { expect, test } from "@playwright/test";

test("Review item shows LLM project routing summary and reason", async ({ page }) => {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        user: {
          id: "demo-admin",
          email: "admin@paraworks.com",
          role: "admin",
          permission_levels: ["public", "internal", "restricted"],
          name: "ParaWorks Admin",
          title: "Workspace Administrator",
          department: "Platform",
        },
      },
    });
  });
  await page.route("**/api/v1/projects/defined", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        projects: [
          { project_key: "project-alpha", name: "Project Alpha", summary: "Redis queue work" },
        ],
      },
    });
  });
  await page.route("**/api/v1/review?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        total_count: 1,
        limit: 50,
        offset: 0,
        has_more: false,
        items: [
          {
            id: 1,
            item_type: "history_event",
            status: "pending_review",
            permission_level: "internal",
            confidence_score: 0.91,
            source_links: ["https://example.slack.com/archives/C123/p1777600800000100"],
            source_snippets: ["Redis queue 상태를 확인하고 sync job을 복구합니다."],
            payload: {
              title: "Redis 큐 상태 확인",
              summary: "Redis 큐와 동기화 작업 상태를 확인했습니다.",
              agent_name: "slack_agent",
              project_key: "project-alpha",
              project_name: "Project Alpha",
              project_assignment_method: "llm_tool",
              project_assignment_summary: "Redis 큐 상태와 동기화 안정성 개선 논의입니다.",
              project_assignment_reason: "Redis와 sync job 근거가 Project Alpha와 일치합니다.",
              project_assignment_confidence: 0.86,
            },
            agent_run_id: 10,
            agent_run_details: {
              model_name: "gpt-5-mini",
              prompt_version: "slack-taxonomy:v4-project-tool",
              estimated_cost_usd: 0.00006,
              total_tokens: 210,
            },
          },
        ],
        groups: [],
      },
    });
  });
  await page.route("**/api/v1/review/*/promotion-preview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        target_type: "history_event",
        can_approve: true,
        missing_required_fields: [],
        normalized_payload: { title: "Redis 큐 상태 확인", reason: "Redis 큐와 동기화 작업 상태를 확인했습니다." },
      },
    });
  });

  await page.addInitScript(() => window.localStorage.setItem("paraworks-demo-user", "demo-admin"));
  await page.goto("/review");

  await expect(page.getByText("LLM 프로젝트 분류")).toBeVisible();
  await expect(page.getByText("Redis 큐 상태와 동기화 안정성 개선 논의입니다.")).toBeVisible();
  await expect(page.getByText("Redis와 sync job 근거가 Project Alpha와 일치합니다.")).toBeVisible();
});
```

- [ ] **단계 2: 실패 상태(RED)를 확인한다**

Run:

```powershell
cd frontend
npm.cmd run test:visual -- review-project-routing.spec.ts --project=chromium-desktop
```

Expected:

```text
FAIL: "LLM 프로젝트 분류" text not found
```

- [ ] **단계 3: Review UI helper를 추가한다**

`frontend/src/app/review/page.tsx`에 helper를 추가한다.

```typescript
function projectRoutingLabel(item: ReviewItem) {
  return item.payload.project_assignment_method === "llm_tool"
    ? "LLM 프로젝트 분류"
    : undefined;
}

function projectRoutingSummary(item: ReviewItem) {
  const summary = item.payload.project_assignment_summary;
  return typeof summary === "string" && summary.trim() ? summary : undefined;
}

function projectRoutingReason(item: ReviewItem) {
  const reason = item.payload.project_assignment_reason;
  return typeof reason === "string" && reason.trim() ? reason : undefined;
}
```

- [ ] **단계 4: Review card에 표시 영역을 추가한다**

Review item card 내부의 프로젝트 선택 UI 근처에 추가한다.

```tsx
{projectRoutingLabel(item) ? (
  <div className="rounded-lg border border-[var(--line-soft)] bg-[var(--glass-strong)] p-3 text-sm">
    <p className="text-xs font-semibold text-[var(--ink-muted)]">{projectRoutingLabel(item)}</p>
    {projectRoutingSummary(item) ? (
      <p className="mt-1 font-medium text-[var(--ink-strong)]">{projectRoutingSummary(item)}</p>
    ) : null}
    {projectRoutingReason(item) ? (
      <p className="mt-1 leading-5 text-[var(--ink-muted)]">{projectRoutingReason(item)}</p>
    ) : null}
  </div>
) : null}
```

- [ ] **단계 5: 통과 상태(GREEN)를 확인한다**

Run:

```powershell
cd frontend
npm.cmd run test:visual -- review-project-routing.spec.ts --project=chromium-desktop
```

Expected:

```text
1 passed
```

---

## 작업 8: 승인 후 프로젝트 활동 연결 회귀 테스트

**대상 파일:**
- 테스트: `backend/tests/test_project_memory_api.py`

- [ ] **단계 1: 승인된 LLM project routing 항목이 프로젝트 타임라인에 보이는 테스트를 추가한다**

```python
def test_approved_slack_llm_project_routing_item_appears_in_project_timeline(
    client,
    db_session: Session,
) -> None:
    project = Project(
        project_key='project-alpha',
        name='Project Alpha',
        summary='Redis queue status and sync job reliability work',
    )
    db_session.add(project)
    db_session.flush()
    item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Redis 큐 상태 확인',
            'summary': 'Redis 큐와 동기화 작업 상태를 확인했습니다.',
            'project_key': 'project-alpha',
            'project_name': 'Project Alpha',
            'project_assignment_method': 'llm_tool',
            'project_assignment_summary': 'Redis 큐 상태와 동기화 안정성 개선 논의입니다.',
            'project_assignment_reason': 'Redis와 sync job 근거가 Project Alpha와 일치합니다.',
        },
        source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
        source_snippets=['Redis queue 상태를 확인하고 sync job을 복구합니다.'],
        confidence_score=0.91,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()

    approve_response = client.post(f'/api/v1/review/{item.id}/approve')
    assert approve_response.status_code == 200

    projects_response = client.get('/api/v1/projects')
    assert projects_response.status_code == 200
    project_payload = next(
        project for project in projects_response.json()['projects']
        if project['project_key'] == 'project-alpha'
    )

    assert any(
        timeline_item['title'] == 'Redis 큐 상태 확인'
        for timeline_item in project_payload['timeline_items']
    )
```

- [ ] **단계 2: 테스트를 실행한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py::test_approved_slack_llm_project_routing_item_appears_in_project_timeline -q
```

Expected:

```text
1 passed
```

이 테스트는 기존 project_key promotion 흐름이 이미 맞다면 바로 통과할 수 있다. 바로 통과하면 새 기능의 승격 계약이 기존 구현과 호환된다는 의미로 기록한다.

---

## 작업 9: 통합 검증

**대상 파일:** 없음. 검증 명령만 실행한다.
- No production file changes

- [ ] **단계 1: Backend targeted tests를 실행한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_slack_project_routing.py backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **단계 2: Ruff를 실행한다**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run ruff check agent_slack/project_routing.py agent_slack/agent_slack.py backend/app/agents/slack_agent/sync_service.py backend/app/api/v1/integrations.py backend/app/projects/classifier.py backend/tests/test_agent_slack_project_routing.py backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py
```

Expected:

```text
All checks passed!
```

- [ ] **단계 3: Frontend checks를 실행한다**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run lint
npm.cmd run build
npm.cmd run test:visual -- review-project-routing.spec.ts
```

Expected:

```text
typecheck passed
lint passed
build passed
Playwright desktop/mobile passed
```

- [ ] **단계 4: 실제 로컬 서버 Playwright smoke를 실행한다**

전제:

- backend와 frontend dev server가 실행 중이어야 한다.
- live LLM key가 있으면 실제 provider 호출 비용이 발생할 수 있으므로, 테스트 계정/작은 Slack window에서만 확인한다.

확인 항목:

```text
1. 프로젝트 탭에서 Project Alpha 같은 테스트 프로젝트를 생성한다.
2. Slack 동기화를 실행한다.
3. 검토사항에서 Slack Agent 후보가 생성되는지 확인한다.
4. 후보 카드에 LLM 프로젝트 분류, 프로젝트 요약, 연결 근거가 보이는지 확인한다.
5. 프로젝트 select에서 사용자가 다른 프로젝트로 변경할 수 있는지 확인한다.
6. 승인 후 타임라인/프로젝트 탭에 해당 프로젝트 활동으로 표시되는지 확인한다.
```

---

## 작업 10: 문서 갱신

**대상 파일:**
- 수정: `agent_slack/20260514_project_timeline_rag_progress.md`
- 수정: `docs/portfolio-log.md`
- 수정: `docs/superpowers/runbooks/session-handoff.md`

- [ ] **단계 1: `agent_slack` 진행 문서를 갱신한다**

추가할 내용:

```markdown
## 2026-05-15 Slack 프로젝트 Router Tool Agent

- Slack Agent에 LangChain tool-calling 기반 프로젝트 분류 노드를 추가했다.
- 등록 프로젝트 목록은 DB에서 읽어 `agent_slack`으로 전달한다.
- Agent는 `list_registered_projects`, `score_project_candidates` tool을 사용해 프로젝트를 선택한다.
- 검토 항목 페이로드에 `project_assignment_method=llm_tool`, 프로젝트 요약, 연결 근거, 확신도, 대체 후보를 보존한다.
- LLM project routing이 실행된 Slack sync에서는 기존 규칙 기반 project_assignment 중복 생성을 건너뛴다.
- 검증 명령과 결과를 기록한다.
```

- [ ] **단계 2: portfolio log를 갱신한다**

추가할 내용:

```markdown
- `feat: Slack 프로젝트 Router Tool Agent 추가`
  - Slack Agent 흐름 안에 LangChain tool-calling 기반 프로젝트 router를 추가했다.
  - Router는 프로젝트를 선택하기 전에 등록 프로젝트 조회 tool과 deterministic 후보 점수 tool을 사용한다.
  - 검토 항목은 LLM이 생성한 프로젝트 요약, 연결 근거, 확신도, 대체 후보를 보존한다.
  - 검증: 관련 백엔드 테스트, 프론트엔드 빌드, Playwright review routing 확인을 통과했다.
```

- [ ] **단계 3: handoff 문서를 갱신한다**

추가할 내용:

```markdown
## 2026-05-15 Slack 프로젝트 Router Tool Agent 인수인계

- 주요 파일:
  - `agent_slack/project_routing.py`
  - `agent_slack/agent_slack.py`
  - `backend/app/agents/slack_agent/sync_service.py`
  - `backend/app/api/v1/integrations.py`
  - `frontend/src/app/review/page.tsx`
- 주의:
  - 테스트에서 live LLM을 호출하지 않는다.
  - Review 승인 전까지 LLM project routing 결과는 trusted knowledge가 아니다.
  - Slack LLM routing이 실행된 경우 deterministic project_assignment 중복 생성을 막아야 한다.
```

---

## 위험 요소와 방어 장치

- **비용 증가:** 프로젝트 라우팅은 추출 후보와 등록 프로젝트 목록만 입력으로 사용한다. 전체 Slack corpus를 다시 보내지 않는다.
- **프로젝트 오분류:** 낮은 확신도 또는 근거 부족이면 `needs_user_selection=true`로 두고 Review UI에서 사용자가 직접 선택한다.
- **중복 ReviewItem:** Slack LLM path에서는 deterministic `project_assignment`를 skip한다.
- **권한 상승 위험:** source evidence permission level을 그대로 유지하며 project routing 결과가 permission level을 넓히지 않는다.
- **테스트에서 live API 호출 위험:** 모든 테스트는 fake model 또는 monkeypatch된 `process_daily_slack_sync`를 사용한다.

---

## 자체 검토

- 요구사항 반영 범위:
  - LangChain tool 방식: 작업 1, 작업 2에서 `@tool`, `create_agent`, tool-calling wrapper를 구현한다.
  - 기존 `agent_slack`에 추가: 작업 3에서 LangGraph 노드로 연결한다.
  - 프로젝트 요약 필요: 작업 2, 작업 5에서 `assignment_summary`, `assignment_reason`을 생성/저장한다.
  - 사용자 확인 필요: 작업 7에서 Review UI에 요약/근거를 표시하고 기존 프로젝트 선택 UI와 함께 사용한다.
  - Review Queue boundary: 모든 결과는 검토 항목 페이로드에만 저장되고 승인 전 trusted knowledge로 승격하지 않는다.
  - 중복 방지: 작업 6에서 deterministic project_assignment 중복 생성을 막는다.
- 미완성 표식 확인:
  - 비워둔 항목이나 추후 작성 표식이 남아 있지 않다.
  - 각 task에 테스트, 실행 명령, 기대 결과가 있음.
- 타입 일관성:
  - `ProjectOption`, `ProjectRoutingDecision`, `ProjectRoutingResult` 이름을 전 task에서 동일하게 사용한다.
  - payload field는 `project_assignment_*` prefix로 통일한다.
