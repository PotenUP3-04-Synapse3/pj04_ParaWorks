# 개발자 C Gmail/Google Drive 통합 작업 문서

작성일: 2026-05-15  
담당자: 개발자 C  
범위: Gmail, Google Drive 고도화 중 공용 계약, 검토 승인, 프로젝트/타임라인/RAG 연결

## 목표

개발자 B가 만든 Gmail/Drive Mail/Document Agent 결과를 ParaWorks 제품 흐름에 연결한다.

최종 흐름은 다음과 같다.

1. Gmail 또는 Google Drive 동기화
2. Mail/Document Agent가 업무 후보와 프로젝트 라우팅 결과를 ReviewItem으로 저장
3. Review 화면에서 사용자가 프로젝트를 확인하거나 선택
4. 프로젝트가 없는 항목은 승인 불가
5. 승인된 항목이 프로젝트별 타임라인과 프로젝트 탭에 표시
6. 승인된 source chunk와 approved knowledge가 RAG indexing 대상에 포함

개발자 C는 3~6번과 공용 계약을 맡는다. Gmail/Drive connector 세부 파싱과 Mail/Document Agent 추출 prompt는 개발자 B가 맡는다.

## 담당 파일

개발자 C가 수정할 수 있는 기본 영역은 아래로 제한한다.

- `backend/app/agent_runtime/project_routing.py`
- `backend/app/agent_runtime/`
- `backend/app/knowledge/promotion.py`
- `backend/app/api/v1/review.py`
- `backend/app/api/v1/integrations.py`
- `backend/app/projects/service.py`
- `backend/app/rag/indexing.py`
- `backend/app/agent_runtime/company_memory.py`
- `frontend/src/app/review/`
- `frontend/src/app/timeline/`
- `frontend/src/app/projects/`
- `frontend/e2e/`
- 관련 backend/frontend 테스트

## 건드리지 않을 영역

분업 충돌을 줄이기 위해 아래 영역은 직접 수정하지 않는다.

- `agent_slack/`
- `backend/app/agents/slack_agent/`
- `backend/app/connectors/google.py`
- `backend/app/agents/mail_document_agent/agent.py`
- `backend/app/agents/mail_document_agent/llm.py`
- `backend/app/agents/mail_document_agent/service.py`

Mail/Document Agent 쪽 변경이 필요하면 개발자 B에게 요청한다. 단, 공용 계약 import 경로 변경처럼 B와 합의된 작은 연결 작업은 별도 커밋으로 분리한다.

## 작업 1. 공용 프로젝트 라우팅 계약 제공

Slack 전용 `agent_slack/project_routing.py`를 Gmail/Drive에서 직접 import하지 않도록 공용 계약을 만든다.

예상 위치:

- `backend/app/agent_runtime/project_routing.py`

필수 모델:

- `ProjectOption`
- `ProjectRoutingCandidate`
- `ProjectRoutingDecision`
- `ProjectRoutingResult`

필수 함수 또는 Protocol:

- `ProjectRouterModel`
- `route_projects_for_candidates()`
- `apply_project_routing_to_payload()` 또는 동일 역할 helper

계약 규칙:

- 등록 프로젝트로 판단되면 `project_key`를 채운다.
- 판단 근거가 부족하면 `project_key=None`, `needs_user_selection=True`로 둔다.
- 라우터는 모든 후보에 대해 decision을 반환해야 한다.
- 라우터 결과는 trusted knowledge가 아니라 ReviewItem payload에만 저장된다.
- 테스트에서는 fake router를 사용한다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_runtime_project_routing.py -q
```

## 작업 2. 승인 정책 정리

Gmail/Drive Mail/Document Agent가 만든 `todo`, `decision_record`, `history_event`, `timeline_event` 후보는 프로젝트가 확정되어야 승인 가능해야 한다.

적용 위치:

- `backend/app/knowledge/promotion.py`
- `backend/app/api/v1/review.py`

승인 불가 조건:

- `payload.agent_name == 'mail_document_agent'`
- `payload.project_assignment_method == 'llm_tool'`
- `payload.project_key`가 비어 있음
- 또는 `payload.project_needs_user_selection == true`

이 경우 promotion preview와 approve API가 모두 같은 이유를 반환해야 한다.

사용자에게 보여줄 의미:

- "프로젝트를 선택해야 승인할 수 있습니다."
- "등록 프로젝트와 자동 매칭되지 않아 사용자 확인이 필요합니다."

주의:

- legacy `project_assignment` item의 승인 정책과 섞지 않는다.
- Slack Agent 승인 정책을 깨지 않는다.
- ReviewItem을 승인하면서 source evidence를 삭제하지 않는다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q
```

## 작업 3. Review API와 UI 연결

Review 화면은 Slack과 Gmail/Drive를 같은 방식으로 보여야 한다.

필수 UI 동작:

- Mail/Document Agent 항목에도 "LLM 프로젝트 분류" 또는 동일한 의미의 한국어 표시가 나온다.
- 프로젝트가 자동 선택된 경우 select에 해당 프로젝트가 선택되어 있다.
- 프로젝트가 미확정이면 "프로젝트 선택" 상태로 보인다.
- 프로젝트 미확정 항목은 승인 버튼이 비활성화된다.
- 사용자가 등록 프로젝트 중 하나를 선택하면 승인 가능 상태가 된다.
- 선택한 프로젝트는 `PATCH /api/v1/review/{id}`로 `project_key`, `project_name`, `project_needs_user_selection=false`가 저장된다.

성능 기준:

- 검토 항목이 200개 수준이어도 첫 화면 렌더링이 급격히 느려지면 안 된다.
- 이번 범위에서 큰 구조 변경이 어렵다면 최소한 promotion preview 호출을 화면에 보이는 항목 중심으로 제한하거나 중복 호출을 줄인다.

권장 Playwright 테스트:

- Gmail 후보가 프로젝트 자동 선택 상태로 표시된다.
- Drive 후보가 프로젝트 미확정 상태로 표시되고 승인 버튼이 막힌다.
- 프로젝트를 수동 선택하면 승인 가능해진다.

권장 명령:

```powershell
cd frontend
npm.cmd run test:visual -- review-project-routing.spec.ts
```

## 작업 4. 프로젝트와 타임라인 반영

승인된 Gmail/Drive 항목은 프로젝트별 활동으로 보여야 한다.

적용 위치:

- `backend/app/projects/service.py`
- `frontend/src/app/timeline/`
- `frontend/src/app/projects/`

필수 동작:

- 타임라인 탭에는 등록된 프로젝트만 표시한다.
- 승인된 Gmail/Drive `todo`, `decision_record`, `history_event`, `timeline_event`가 `project_key` 기준으로 프로젝트에 연결된다.
- 타임라인은 날짜 단위로 묶어서 표시한다.
- 프로젝트 탭의 활동 영역에 Gmail/Drive 승인 항목이 반영된다.
- 프로젝트 탭에서 근거, 활동, 검토 영역이 겹치지 않는다.

주의:

- 승인된 지식은 Review Queue에서 사라질 수 있지만 DB에서는 삭제하지 않는다.
- `project_assignment` legacy item만 프로젝트 활동으로 보지 않는다.
- 동일한 source evidence가 중복으로 두 번 보이는 경우 source id 기준 dedupe를 적용한다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py -q
cd frontend
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts
npm.cmd run test:visual -- projects-responsive-metrics.spec.ts
```

## 작업 5. RAG indexing 연결

승인된 Gmail/Drive evidence가 RAG indexing에 들어가야 한다.

적용 위치:

- `backend/app/rag/indexing.py`

필수 동작:

- 승인된 ReviewItem payload의 `source_ids`에 포함된 Gmail/Drive Source.source_id만 원본 chunk indexing 대상이 된다.
- 승인된 DecisionRecord, HistoryEvent, Todo, TimelineEvent는 approved knowledge 경로로 indexing 대상이 된다.
- 승인되지 않은 Gmail/Drive 원본 chunk는 RAG에 들어가지 않는다.
- permission level과 source snippet이 유지된다.
- content hash가 같으면 재임베딩을 건너뛴다.

주의:

- SQLite smoke mode에서는 production vector write를 하지 않는다.
- 테스트에서는 deterministic embedding 또는 fake writer만 사용한다.
- live embedding provider를 호출하지 않는다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_rag_indexing.py -q
```

## 작업 6. 통합 API 정리

Gmail/Drive sync 이후 ReviewItem 생성 경로가 중복되지 않게 정리한다.

적용 위치:

- `backend/app/api/v1/integrations.py`

필수 동작:

- Gmail/Drive sync가 완료되면 Mail/Document Agent ReviewItem 생성 경로가 호출된다.
- Source가 이미 있고 ReviewItem만 삭제된 상황에서는 기존 source로 ReviewItem을 복구할 수 있다.
- Mail/Document Agent가 LLM tool 방식으로 프로젝트 라우팅을 저장한 경우 별도의 규칙 기반 `project_assignment`를 추가로 만들지 않는다.
- 응답 metadata에는 created review item 수, changed source 수, skipped duplicate 수가 유지된다.

주의:

- Slack sync 경로를 직접 수정하지 않는다.
- Google connector parsing 품질 문제는 개발자 B 영역이다.
- deterministic `project_assignment`는 legacy fallback으로만 남기고 Gmail/Drive 신규 agent 결과와 중복 생성하지 않는다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mock_sync.py backend/tests/test_mail_document_agent_api.py -q
```

## 작업 7. Company Memory orchestration 연결

오케스트레이션에서 Gmail/Drive Mail/Document Agent 결과가 같은 Review Queue boundary를 통과해야 한다.

적용 위치:

- `backend/app/agent_runtime/company_memory.py`

필수 동작:

- 오케스트레이션은 Mail/Document Agent가 만든 ReviewItem을 trusted knowledge로 바로 승격하지 않는다.
- `hitl_checkpoint`에는 Gmail/Drive ReviewItem id가 포함된다.
- 비용 계획에 Gmail/Drive evidence 수와 token estimate가 유지된다.
- 프로젝트 라우팅 metadata가 있으면 AgentRun detail에서 확인 가능해야 한다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_runtime.py backend/tests/test_mail_document_agent_api.py -q
```

## 작업 8. Playwright 통합 테스트

Gmail/Drive 고도화는 화면에서 확인할 수 있어야 한다.

권장 시나리오:

1. mock Gmail sync 또는 API fixture로 Mail/Document Agent ReviewItem 생성
2. `/review`에서 Gmail 후보 확인
3. 프로젝트 자동 선택 또는 수동 선택 확인
4. 승인 실행
5. `/timeline`에서 해당 프로젝트 날짜 그룹에 표시되는지 확인
6. `/projects`에서 해당 프로젝트 활동에 표시되는지 확인
7. Drive 후보도 같은 흐름으로 확인

테스트 파일 예시:

- `frontend/e2e/gmail-drive-project-routing-flow.spec.ts`
- `frontend/e2e/review-project-routing.spec.ts` 보강
- `frontend/e2e/timeline-project-date-groups.spec.ts` 보강
- `frontend/e2e/projects-responsive-metrics.spec.ts` 보강

권장 명령:

```powershell
cd frontend
npm.cmd run test:visual -- gmail-drive-project-routing-flow.spec.ts
npm.cmd run test:visual -- review-project-routing.spec.ts
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts
npm.cmd run test:visual -- projects-responsive-metrics.spec.ts
```

## 완료 기준

개발자 C 작업은 아래 조건을 만족하면 완료로 본다.

- 공용 프로젝트 라우팅 계약이 `backend/app/agent_runtime/`에 있다.
- Gmail/Drive Mail/Document Agent ReviewItem이 프로젝트 미확정이면 승인할 수 없다.
- 사용자가 Review 화면에서 프로젝트를 선택하면 승인할 수 있다.
- 승인된 Gmail/Drive 항목이 프로젝트별 타임라인에 날짜 단위로 표시된다.
- 승인된 Gmail/Drive 항목이 프로젝트 탭 활동에 표시된다.
- 승인된 Gmail/Drive source chunk와 approved knowledge가 RAG indexing 대상이 된다.
- 규칙 기반 `project_assignment`가 Gmail/Drive LLM tool 결과와 중복 생성되지 않는다.
- Playwright로 Review, Timeline, Projects 화면 흐름을 검증했다.

최소 검증 명령:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_agent_runtime_project_routing.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_project_memory_api.py backend/tests/test_rag_indexing.py backend/tests/test_mock_sync.py backend/tests/test_mail_document_agent_api.py -q
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run lint
npm.cmd run build
npm.cmd run test:visual -- gmail-drive-project-routing-flow.spec.ts
```

## 개발자 B에게 요청할 수 있는 것

아래가 필요하면 개발자 B에게 요청한다.

- Gmail source metadata 추가
- Drive parser metadata 추가
- Mail/Document Agent prompt 또는 fake model 변경
- Mail/Document Agent ReviewItem payload 생성 위치 변경
- Gmail 본문+첨부 grouping 변경
- Drive 파일 grouping 변경

개발자 C는 위 항목을 직접 수정하지 않는다.

