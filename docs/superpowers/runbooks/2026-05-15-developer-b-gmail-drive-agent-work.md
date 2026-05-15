# 개발자 B Gmail/Google Drive Agent 고도화 작업 문서

작성일: 2026-05-15  
담당자: 개발자 B  
범위: Gmail, Google Drive 고도화 중 Mail/Document Agent와 Google connector 품질 개선

## 목표

Gmail과 Google Drive에서 가져온 데이터를 Slack Agent 방식과 같은 흐름으로 처리한다.

최종 흐름은 다음과 같다.

1. Gmail 또는 Google Drive 동기화
2. Source, Document, DocumentVersion, DocumentChunk 저장
3. Mail/Document Agent가 증거 묶음을 읽고 업무 후보를 추출
4. 등록된 프로젝트 목록을 기준으로 LLM tool 기반 프로젝트 분류 수행
5. ReviewItem을 `pending_review`로 저장
6. 사용자가 검토 사항 화면에서 프로젝트를 확인하거나 바꾼 뒤 승인

개발자 B는 1~5번 중 Gmail/Drive 수집 품질과 Mail/Document Agent 후보 생성 품질을 맡는다. 승인 이후 타임라인, 프로젝트 탭, RAG 반영은 개발자 C가 맡는다.

## 담당 파일

개발자 B가 수정할 수 있는 기본 영역은 아래로 제한한다.

- `backend/app/connectors/google.py`
- `backend/app/agents/mail_document_agent/`
- `backend/tests/test_google_connector.py`
- `backend/tests/test_mail_document_agent.py`
- `backend/tests/test_mail_document_agent_review_bridge.py`
- `backend/tests/test_mail_document_agent_api.py`

필요한 경우에만 아래 테스트 파일을 보강한다.

- `backend/tests/test_connector_factory.py`
- `backend/tests/test_mock_sync.py` 중 Gmail/Drive Mail/Document Agent 호출 검증에 한정

## 건드리지 않을 영역

분업 충돌을 줄이기 위해 아래 영역은 수정하지 않는다.

- `agent_slack/`
- `backend/app/agents/slack_agent/`
- `backend/app/projects/classifier.py`
- `backend/app/knowledge/promotion.py`
- `backend/app/projects/service.py`
- `backend/app/rag/`
- `backend/app/agent_runtime/company_memory.py`
- `backend/app/api/v1/review.py`
- `frontend/`

위 영역 수정이 필요해 보이면 직접 수정하지 말고 개발자 C에게 요청한다.

## 선행 조건

개발자 C가 공용 프로젝트 라우팅 계약을 먼저 제공한다.

예상 위치:

- `backend/app/agent_runtime/project_routing.py`

Mail/Document Agent는 Slack 전용 파일인 `agent_slack/project_routing.py`를 import하지 않는다. Gmail/Drive, Slack, 향후 다른 Agent가 모두 재사용해야 하므로 공용 계약은 `backend/app/agent_runtime/` 아래에 있어야 한다.

## ReviewItem payload 계약

Mail/Document Agent가 만드는 ReviewItem에는 기존 증거 필드와 프로젝트 분류 필드를 함께 보존해야 한다.

기존 필수 증거 필드:

- `source_ids`
- `source_types`
- `source_urls`
- `source_authors`
- `agent_name`
- `agent_run_id`
- `prompt_version`
- `cache_key`
- `estimated_cost_usd`
- `token_usage`
- `uncertainty_reason`

프로젝트 분류 필드:

- `project_assignment_method`: 항상 `llm_tool`
- `project_key`: 등록 프로젝트로 판단된 경우에만 저장
- `project_name`: 등록 프로젝트로 판단된 경우에만 저장
- `project_assignment_summary`: 프로젝트에 연결되는 이유를 사용자가 읽을 수 있는 한국어 문장으로 요약
- `project_assignment_reason`: 어떤 증거와 프로젝트 설명을 비교했는지 설명
- `project_assignment_confidence`: 0~1 숫자
- `project_alternatives`: 대안 프로젝트 key 또는 이름 목록
- `project_needs_user_selection`: 프로젝트를 확정하지 못했으면 `true`

프로젝트를 확정하지 못한 경우 `project_key`를 임의로 채우지 않는다. `project_tag`, 파일명, 메일 제목만으로 fallback 프로젝트를 지정하지 않는다.

## 작업 1. Gmail/Drive source 품질 보강

목표는 Agent가 판단에 쓸 수 있는 증거를 안정적으로 보존하는 것이다.

Gmail SourceEvent에서 보존해야 할 정보:

- Gmail message id
- thread id
- subject
- from, to, cc
- date header 또는 internal date
- source URL
- 본문 snippet
- attachment가 있으면 parent message id
- attachment 파일명, mime type, attachment id
- permission level
- content signature 또는 dedupe 가능한 metadata

Drive SourceEvent에서 보존해야 할 정보:

- Drive file id
- file name
- mime type
- webViewLink
- createdTime, modifiedTime
- owner 또는 lastModifyingUser
- version
- headRevisionId
- parser status
- parser status reason
- parser adapter name
- content signature
- source snippet
- permission level

테스트 기준:

- Gmail 본문과 첨부가 같은 메일 단위로 묶일 수 있는 metadata를 가진다.
- Drive 문서는 파일 단위로 독립 증거가 된다.
- parser가 본문을 읽지 못해도 metadata-only 증거로 남고 `uncertainty_reason`을 만들 수 있다.
- live Gmail/Drive API를 호출하지 않고 fake client만 사용한다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_google_connector.py -q
```

## 작업 2. Mail/Document Agent 추출 품질 개선

현재 Mail/Document Agent는 `EvidencePacket`을 받아 `ReviewCandidate`를 만든다. 이 구조는 유지한다.

개선 대상:

- Gmail/Drive 공통으로 업무 내용이 아닌 개인 잡담, 알림성 문구, 서명, 자동 footer를 ReviewItem으로 만들지 않는다.
- Gmail은 메일 제목, 발신자, 본문, 첨부 요약을 함께 보고 판단한다.
- Drive는 문서 제목만 보지 않고 본문 chunk와 parser metadata를 함께 본다.
- `todo`, `decision_record`, `history_event` 중 하나로 분류한다.
- 불확실하면 낮은 confidence와 `uncertainty_reason`을 남긴다.
- 증거가 없으면 ReviewItem을 만들지 않는다.

Mail/Document Agent prompt는 한국어 업무 검토자가 읽을 결과를 만들도록 조정한다. 단, 테스트에서는 live LLM을 호출하지 않고 fake model을 사용한다.

추가로 구조화 필드에 담을 수 있는 값:

- `business_context`
- `task_summary`
- `recommended_next_step`
- `assignee`
- `due_date`
- `counterparty`
- `source_subject`
- `document_title`
- `document_parser_status`

예약 필드는 덮어쓰지 않는다.

- `title`
- `summary`
- `agent_name`
- `agent_run_id`
- `prompt_version`
- `cache_key`
- `estimated_cost_usd`
- `token_usage`
- `uncertainty_reason`
- `source_ids`
- `source_types`
- `source_urls`
- `source_authors`

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mail_document_agent.py -q
```

## 작업 3. Gmail/Drive grouping 유지

기존 grouping 정책은 유지한다.

- Gmail 본문과 Gmail 첨부는 같은 메일 단위로 묶는다.
- Drive 파일은 파일 단위로 분리한다.

수정 위치:

- `backend/app/agents/mail_document_agent/service.py`
- `_changed_source_groups()`
- `create_mail_document_agent_review_items_for_changed_sources()`

주의할 점:

- Gmail 첨부만 따로 ReviewItem으로 만들면 원문 맥락이 사라진다.
- 서로 다른 Drive 파일을 하나의 ReviewItem으로 묶으면 프로젝트 판단과 승인의 단위가 흐려진다.
- grouping 이후에도 `source_ids`는 묶음 안의 모든 Source.source_id를 보존한다.

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mail_document_agent_review_bridge.py -q
```

## 작업 4. 프로젝트 라우팅 적용

개발자 C가 공용 라우팅 계약을 제공하면 Mail/Document Agent 저장 경로에 연결한다.

예상 적용 위치:

- `backend/app/agents/mail_document_agent/service.py`

처리 순서:

1. `build_mail_document_evidence_packet()`으로 증거 묶음 생성
2. `MailDocumentAgent.run(packet)` 실행
3. 생성된 `ReviewCandidate` 목록을 프로젝트 라우터에 전달
4. 라우터 결과를 candidate payload에 반영
5. ReviewItem 저장

라우터 입력에는 최소한 아래 정보가 들어가야 한다.

- candidate title
- candidate summary
- candidate item_type
- candidate confidence_score
- source links
- source snippets
- source types
- source ids
- evidence text
- 등록 프로젝트 목록의 project_key, name, summary

라우터 결과 적용 규칙:

- 확정 프로젝트가 있으면 `project_key`, `project_name`을 저장한다.
- 확정 프로젝트가 없으면 `project_key`를 비우고 `project_needs_user_selection=true`를 저장한다.
- 모든 경우에 `project_assignment_method='llm_tool'`을 저장한다.
- fallback 규칙 기반 프로젝트 연결을 만들지 않는다.

AgentRun metadata에는 프로젝트 라우팅 실행 정보를 남긴다.

필수 metadata:

- `project_routing.enabled`
- `project_routing.method`
- `project_routing.project_count`
- `project_routing.model_name`
- `project_routing.input_tokens`
- `project_routing.output_tokens`

권장 테스트:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py -q
```

## 작업 5. 비용과 캐시 정보 보존

Mail/Document Agent의 기존 비용 기록을 깨지 않는다.

보존해야 할 값:

- `AgentRun.input_tokens`
- `AgentRun.output_tokens`
- `AgentRun.total_tokens`
- `AgentRun.estimated_cost_usd`
- `ReviewItem.payload.token_usage`
- `ReviewItem.payload.estimated_cost_usd`
- `ReviewItem.payload.cache_key`

프로젝트 라우터가 별도 토큰을 사용한다면 AgentRun metadata에 추가로 기록하고, 전체 비용 합산 정책이 필요하면 개발자 C에게 맡긴다.

## 작업 6. 완료 기준

개발자 B 작업은 아래 조건을 만족하면 완료로 본다.

- Gmail 본문+첨부 grouping이 유지된다.
- Drive 파일 단위 grouping이 유지된다.
- Mail/Document Agent ReviewItem이 `source_ids`, `source_urls`, `source_snippets`, permission을 보존한다.
- 프로젝트 라우팅 결과가 Slack Agent와 같은 payload 필드명으로 저장된다.
- 프로젝트 미확정 항목은 `project_needs_user_selection=true`이고 `project_key`가 비어 있다.
- fake model과 fake connector 테스트만으로 검증된다.
- live Gmail, live Drive, live LLM API를 테스트에서 호출하지 않는다.

최소 검증 명령:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_google_connector.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py -q
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run ruff check backend/app/connectors/google.py backend/app/agents/mail_document_agent backend/tests/test_google_connector.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py
```

## 개발자 C에게 전달할 산출물

작업 완료 후 개발자 C가 통합할 수 있도록 아래를 남긴다.

- 새로 추가되거나 변경된 ReviewItem payload 필드 목록
- Gmail/Drive source grouping 규칙
- 프로젝트 라우팅 no-match 예시 payload
- AgentRun metadata 예시
- 통과한 테스트 명령과 결과

