# Gmail/Google Drive 프로젝트 Tool Routing 분업 가이드

작성일: 2026-05-15  
대상: Mail and Document Agent 담당자, Slack Agent 담당자, 통합 담당자

## 목표

Gmail과 Google Drive에서 들어온 업무 후보도 Slack Agent와 같은 방식으로 등록 프로젝트를 LangChain tool로 확인하고, LLM이 프로젝트 연결 여부를 판단하게 한다.

최종 사용자 흐름은 다음과 같다.

1. Gmail 또는 Google Drive 동기화
2. Mail/Document Agent가 업무 후보인지 판단하고 `decision_record`, `todo`, `history_event`, `timeline_event` 후보 생성
3. 프로젝트 Router가 등록 프로젝트 목록을 tool로 조회
4. Router가 후보별로 등록 프로젝트에 해당하는지 판단
5. 등록 프로젝트에 해당하면 Review의 `프로젝트 지정`에 자동 선택
6. 해당 프로젝트가 없거나 애매하면 `프로젝트 선택` 상태로 두고 사용자 선택 요구
7. 사용자가 프로젝트를 선택하지 않으면 승인 불가
8. 승인하면 타임라인과 프로젝트 탭에 해당 프로젝트 활동으로 반영

## 가장 중요한 분업 원칙

- Gmail/Drive 담당자는 Slack Agent 파일을 직접 수정하지 않는다.
- Slack 담당자는 Mail/Document Agent 파일을 직접 수정하지 않는다.
- 프로젝트 Router의 공용 계약은 `backend/app/agent_runtime/` 아래에 둔다.
- 프론트 Review/Timeline/Projects 같은 공용 UX는 통합 담당자가 맡거나, 한 명이 별도 브랜치에서 처리한다.
- `backend/app/projects/classifier.py`의 규칙 기반 `project_assignment`는 신규 sync 경로에서 점진적으로 제거한다. Gmail/Drive 담당자는 이 파일을 확장하지 않는다.
- live LLM, live Gmail, live Drive API는 테스트에서 호출하지 않는다. fake model과 fake connector만 사용한다.

## 권장 브랜치/소유권

| 작업 | 담당 | 브랜치 예시 | 수정 가능 영역 |
| --- | --- | --- | --- |
| 공용 프로젝트 Router 계약 | 통합 담당자 또는 선행 작업자 | `codex/agent-runtime-project-routing` | `backend/app/agent_runtime/`, 공용 테스트 |
| Slack Agent 통합 | Slack 담당자 | `codex/slack-agent-project-routing` | `agent_slack/`, `backend/app/agents/slack_agent/`, Slack tests |
| Gmail/Drive Agent 통합 | Mail/Document 담당자 | `codex/mail-document-project-routing` | `backend/app/agents/mail_document_agent/`, mail/document tests |
| Review/Timeline/Projects UI와 승인 정책 | 통합 담당자 | `codex/review-project-routing-integration` | `backend/app/knowledge/`, `frontend/src/app/`, e2e tests |

## 공유 계약

공용 계약은 `backend/app/agent_runtime/project_routing.py`에 둔다. Slack 쪽에 이미 있는 `agent_slack/project_routing.py`를 그대로 Mail/Document에서 import하지 않는다. 그 파일은 Slack Agent 소유이기 때문이다.

공용 계약의 최소 형태는 다음과 같다.

```python
from pydantic import BaseModel, Field


class ProjectOption(BaseModel):
    project_key: str
    name: str
    summary: str


class ProjectRoutingCandidate(BaseModel):
    item_index: int
    source_id: str
    title: str
    summary: str
    item_type: str
    source_type: str
    source_links: list[str] = Field(default_factory=list)
    source_snippets: list[str] = Field(default_factory=list)
    evidence_text: str = ''
    confidence_score: float = Field(ge=0, le=1)


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
```

ReviewItem payload에 저장되는 필드는 Slack/Gmail/Drive 모두 동일해야 한다.

```python
{
    'project_key': 'project-alpha',
    'project_name': 'Project Alpha',
    'project_assignment_method': 'llm_tool',
    'project_assignment_summary': '이 후보가 프로젝트에 연결되는 이유를 요약한 한국어 문장',
    'project_assignment_reason': '근거 source와 프로젝트 설명을 비교한 한국어 판단 근거',
    'project_assignment_confidence': 0.86,
    'project_alternatives': ['project-beta'],
    'project_needs_user_selection': False,
}
```

프로젝트를 확정하지 못한 경우에는 `project_key`, `project_name`을 비워 둔다.

```python
{
    'project_assignment_method': 'llm_tool',
    'project_assignment_summary': '등록 프로젝트와 확정 매칭되지 않습니다.',
    'project_assignment_reason': '프로젝트 이름/설명과 source 근거가 충분히 일치하지 않습니다.',
    'project_assignment_confidence': 0.41,
    'project_alternatives': ['project-alpha'],
    'project_needs_user_selection': True,
}
```

## Gmail/Drive 담당자 작업 범위

### 수정할 파일

- `backend/app/agents/mail_document_agent/service.py`
- `backend/app/agents/mail_document_agent/agent.py`
- `backend/app/agents/mail_document_agent/llm.py`
- `backend/tests/test_mail_document_agent_review_bridge.py`
- `backend/tests/test_mail_document_agent_api.py`

### 건드리지 않을 파일

- `agent_slack/*`
- `backend/app/agents/slack_agent/*`
- `frontend/src/app/review/page.tsx`
- `frontend/src/app/timeline/page.tsx`
- `frontend/src/app/projects/page.tsx`
- `backend/app/projects/classifier.py`
- `backend/app/knowledge/promotion.py`

위 파일이 필요해 보이면 통합 담당자에게 별도 작업으로 넘긴다.

## Mail/Document Agent 설계

현재 Mail/Document 경로는 다음 구조다.

```text
Gmail/Drive connector
  -> ingestion
  -> Source / Document / DocumentVersion / DocumentChunk
  -> build_mail_document_evidence_packet()
  -> MailDocumentAgent.run()
  -> ReviewCandidate
  -> ReviewItem(status='pending_review')
```

변경 후 구조는 다음과 같다.

```text
Gmail/Drive connector
  -> ingestion
  -> Source / Document / DocumentVersion / DocumentChunk
  -> build_mail_document_evidence_packet()
  -> MailDocumentAgent.run()
  -> ReviewCandidate
  -> project_route_mail_document_candidates()
  -> ReviewItem(status='pending_review')
```

`project_route_mail_document_candidates()`는 Mail/Document Agent 서비스 내부에 둔다. Slack 파일을 import하지 않는다.

추천 함수 형태:

```python
def project_route_mail_document_candidates(
    *,
    candidates: list[ReviewCandidate],
    packet: EvidencePacket,
    projects: list[ProjectOption],
    router_model: ProjectRouterModel,
) -> ProjectRoutingResult:
    ...
```

후보 payload 적용 helper:

```python
def apply_project_routing_to_candidate(
    candidate: ReviewCandidate,
    decision: ProjectRoutingDecision,
) -> ReviewCandidate:
    payload_fields = {
        **candidate.payload_fields,
        'project_assignment_method': 'llm_tool',
        'project_assignment_summary': decision.assignment_summary,
        'project_assignment_reason': decision.assignment_reason,
        'project_assignment_confidence': decision.confidence_score,
        'project_alternatives': decision.alternatives,
        'project_needs_user_selection': decision.needs_user_selection,
    }
    if decision.project_key:
        payload_fields['project_key'] = decision.project_key
    if decision.project_name:
        payload_fields['project_name'] = decision.project_name
    return replace(candidate, payload_fields=payload_fields)
```

## Gmail과 Drive의 source grouping 유지

Gmail/Drive 담당자는 기존 grouping 정책을 유지한다.

- Gmail 본문과 Gmail 첨부는 같은 메일 단위로 묶는다.
- Google Drive 문서는 파일 단위로 분리한다.
- `create_mail_document_agent_review_items_for_changed_sources()`의 `_changed_source_groups()` 계약은 유지한다.
- 프로젝트 Router는 “후보 단위”로 실행하되, 후보의 source evidence는 기존 group evidence를 그대로 넘긴다.

이유:

- Gmail 첨부만 따로 보면 원문의 업무 맥락을 잃는다.
- Drive 파일 여러 개를 한 후보로 뭉치면 프로젝트 판단과 승인 단위가 흐려진다.

## 프로젝트 Router 입력 구성

Gmail/Drive 후보를 Router에 넘길 때 다음 정보를 포함한다.

```python
ProjectRoutingCandidate(
    item_index=index,
    source_id='|'.join(candidate_source_ids),
    title=candidate.title,
    summary=candidate.summary,
    item_type=candidate.item_type,
    source_type='mail_document',
    source_links=candidate.source_links,
    source_snippets=candidate.source_snippets,
    evidence_text='\n'.join(candidate.source_snippets[:3]),
    confidence_score=candidate.confidence_score,
)
```

`source_id`는 단일 source이면 원래 `Source.source_id`를 사용한다. Gmail 본문+첨부처럼 여러 source가 묶인 경우에는 `|`로 이어 붙인다.

## AgentRun metadata 계약

Mail/Document Agent의 `AgentRun.metadata_`에 다음을 추가한다.

```python
'project_routing': {
    'enabled': bool(project_options),
    'method': 'langchain_tools',
    'project_count': len(project_options),
    'model_name': routing_result.model_name,
    'input_tokens': routing_result.input_tokens,
    'output_tokens': routing_result.output_tokens,
}
```

기존 metadata는 유지한다.

- `source_type`
- `included_source_types`
- `message_count`
- `source_window`
- `selection_strategy`
- `parser_status_counts`
- `cache_hit`
- `evidence_summary`

## 승인 정책

통합 담당자가 `backend/app/knowledge/promotion.py`에서 다음 정책을 공용으로 적용한다.

- `project_assignment_method == "llm_tool"`인 `decision_record`, `todo`, `history_event`, `timeline_event`는 `project_key`가 없으면 승인 불가
- 대상 agent는 `slack_agent`, `mail_document_agent` 모두 포함
- 사용자가 Review UI에서 프로젝트를 선택하면 `PATCH /api/v1/review/{id}`가 `project_key`, `project_name`을 채운다
- 승인 후 `DecisionRecord`, `HistoryEvent`, `Todo`, `TimelineEvent`에 `project_key`가 저장된다

Mail/Document 담당자는 promotion 파일을 직접 고치지 않는다. 대신 자신의 테스트에는 “project_key가 payload에 들어간다”까지만 보장한다.

## UI 작업 경계

통합 담당자가 처리한다.

- Review에서 Gmail/Drive 항목도 `LLM 프로젝트 분류` 카드 표시
- 프로젝트 미선택이면 `프로젝트 선택 후 승인 가능` 안내 표시
- 프로젝트 미선택이면 승인 버튼 비활성화
- `새 프로젝트 만들기` 링크 제공
- Timeline 날짜 그룹 표시
- Project 탭 metric 겹침 방지

Mail/Document 담당자는 UI 파일을 직접 수정하지 않는다.

## 작업 순서

### 1단계: 공용 계약 준비

담당: 통합 담당자

- `backend/app/agent_runtime/project_routing.py` 생성
- `ProjectOption`, `ProjectRoutingCandidate`, `ProjectRoutingDecision`, `ProjectRoutingResult` 정의
- LangChain tool factory와 fake router 테스트 추가
- Slack 기존 `agent_slack/project_routing.py`와 필드명이 어긋나지 않게 맞춤

검증:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_runtime_project_routing.py -q
```

### 2단계: Gmail/Drive Agent 내부 project routing 추가

담당: Mail/Document 담당자

- `backend/app/agents/mail_document_agent/service.py`에 project routing helper 추가
- DB `projects` 테이블에서 등록 프로젝트를 읽어 `ProjectOption`으로 변환
- `create_mail_document_agent_review_items()`에서 `agent.run(packet)` 이후 후보에 routing 적용
- ReviewItem payload에 공용 project routing fields 저장
- AgentRun metadata에 project routing cost/token 정보 저장

검증:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mail_document_agent_review_bridge.py -q
```

### 3단계: Gmail/Drive sync API 회귀 고정

담당: Mail/Document 담당자

- `backend/tests/test_mail_document_agent_api.py`에 Gmail sync와 Drive sync 테스트 추가
- Gmail은 본문+첨부 group에 project routing fields가 보존되는지 확인
- Drive는 파일 단위 ReviewItem에 project routing fields가 보존되는지 확인
- fake router가 project match와 no match를 각각 반환하도록 테스트

검증:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mail_document_agent_api.py -q
```

### 4단계: deterministic `project_assignment` 신규 생성 중단

담당: 통합 담당자

- Slack/Gmail/Drive 신규 sync가 `create_project_assignment_review_items()`에 의존하지 않도록 정리
- `backend/app/projects/classifier.py`는 legacy dry-run 또는 수동 reclassify 전용으로 축소
- `/api/v1/projects/reclassify` 응답에 `strategy: legacy_deterministic_project_classifier`처럼 명확한 이름 사용

검증:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mock_sync.py backend/tests/test_project_memory_api.py -q
```

### 5단계: 승인 정책과 UI 연결

담당: 통합 담당자

- `backend/app/knowledge/promotion.py`에서 `llm_tool` routed item의 `project_key` 필수화
- Review UI에 프로젝트 선택 필요 안내 추가
- Timeline 날짜 그룹 추가
- Project 탭 metric 레이아웃 보강

검증:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_review.py backend/tests/test_project_memory_api.py -q
npm.cmd run test:visual -- review-project-routing-required.spec.ts
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts
npm.cmd run test:visual -- projects-responsive-metrics.spec.ts
```

## Mail/Document 담당자용 테스트 시나리오

### Backend RED/GREEN

1. Gmail 본문+첨부 group이 project routing fields를 받는지 확인
2. Drive 파일 하나가 project routing fields를 받는지 확인
3. Router가 no match를 반환하면 `project_key`가 비어 있고 `project_needs_user_selection=true`인지 확인
4. AgentRun metadata에 `project_routing` token/cost 정보가 남는지 확인
5. source evidence, permission, parser metadata가 routing 이후에도 사라지지 않는지 확인

테스트 예시 이름:

```python
def test_mail_document_agent_routes_gmail_group_with_project_tool(...)
def test_mail_document_agent_routes_drive_file_with_project_tool(...)
def test_mail_document_agent_marks_unmatched_project_for_user_selection(...)
def test_mail_document_agent_project_routing_preserves_evidence_and_permissions(...)
```

### Playwright는 누가 맡는가

Playwright는 통합 담당자가 맡는다. 이유는 Gmail/Drive 담당자가 UI까지 건드리면 작업 영역이 겹치기 때문이다.

다만 Mail/Document 담당자는 route mock에 필요한 fixture shape를 문서화한다.

필수 mock payload:

```json
{
  "item_type": "todo",
  "payload": {
    "agent_name": "mail_document_agent",
    "project_assignment_method": "llm_tool",
    "project_key": "project-alpha",
    "project_name": "Project Alpha",
    "project_assignment_summary": "Gmail 본문과 첨부가 Project Alpha 업무와 연결됩니다.",
    "project_assignment_reason": "메일 제목, 첨부 파일명, 본문 근거가 프로젝트 설명과 일치합니다.",
    "project_assignment_confidence": 0.88,
    "project_needs_user_selection": false,
    "source_ids": ["gmail:message-1", "gmail_attachment:message-1:att-1"],
    "source_types": ["gmail", "gmail_attachment"]
  }
}
```

미선택 mock payload:

```json
{
  "item_type": "history_event",
  "payload": {
    "agent_name": "mail_document_agent",
    "project_assignment_method": "llm_tool",
    "project_assignment_summary": "등록 프로젝트와 확정 매칭되지 않습니다.",
    "project_assignment_reason": "문서 근거와 등록 프로젝트 설명이 충분히 일치하지 않습니다.",
    "project_assignment_confidence": 0.39,
    "project_needs_user_selection": true,
    "source_ids": ["drive:file-unknown"],
    "source_types": ["drive"]
  }
}
```

## 충돌 방지 규칙

- 같은 파일을 두 사람이 동시에 고치지 않는다.
- `backend/app/api/v1/integrations.py`는 충돌 가능성이 크므로 통합 담당자만 수정한다.
- `backend/app/knowledge/promotion.py`도 통합 담당자만 수정한다.
- 공용 contract 변경이 필요하면 먼저 작은 PR 또는 브랜치로 분리한다.
- Mail/Document 담당자는 `agent_slack/project_routing.py`를 복사해 쓰지 않는다.
- Slack 담당자는 `backend/app/agents/mail_document_agent/service.py`에 임시 helper를 넣지 않는다.
- 기존 테스트를 맞추기 위해 live LLM 호출을 추가하지 않는다.

## 병합 순서

1. `codex/agent-runtime-project-routing`
2. `codex/slack-agent-project-routing`
3. `codex/mail-document-project-routing`
4. `codex/review-project-routing-integration`
5. `codex/integration-agent-runtime`

각 브랜치가 merge되기 전 확인할 것:

- agent manifest와 payload contract가 문서와 일치한다.
- ReviewItem은 source links/snippets를 반드시 가진다.
- permission_level은 source evidence 중 가장 엄격한 값을 유지한다.
- token/cost metadata가 AgentRun에 남는다.
- project_key가 없는 `llm_tool` routed item은 승인 전 상태로만 존재한다.

## 완료 기준

- Gmail sync로 생성된 ReviewItem에 `project_assignment_method='llm_tool'`이 들어간다.
- Drive sync로 생성된 ReviewItem에 `project_assignment_method='llm_tool'`이 들어간다.
- Gmail/Drive 후보가 프로젝트에 확정 매칭되면 `project_key`, `project_name`이 채워진다.
- 확정 매칭되지 않으면 `project_key` 없이 `project_needs_user_selection=true`가 저장된다.
- Review 승인 전 source evidence가 유지된다.
- 승인 후 프로젝트 탭과 타임라인 탭에 해당 프로젝트 활동이 표시된다.
- Gmail/Drive 담당자 작업은 Mail/Document Agent 내부와 해당 테스트에 한정된다.
