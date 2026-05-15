# 프로젝트 타임라인과 RAG 표시 진행 기록

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 작업계획서 작성

- 요청: 프로젝트 분류 Agent를 LangChain tool 방식으로 기존 `agent_slack`에 추가하는 작업계획서를 작성했다.
- 현재 코드 기준 판단:
  - 기존 `project_assignment`는 `backend/app/projects/classifier.py`의 규칙 기반 alias matching으로 생성된다.
  - 기존 `agent_slack/agent_slack.py`는 Slack 업무 필터링, 요약, 지식 후보 추출까지 수행하지만 등록 프로젝트를 tool로 조회해 LLM이 프로젝트를 선택하는 단계는 없다.
  - `backend/app/agents/slack_agent/sync_service.py`는 `process_daily_slack_sync()` 결과를 `ReviewItem`으로 저장하므로 project routing metadata를 보존할 위치가 있다.
- 계획서 위치:
  - `docs/superpowers/plans/2026-05-15-slack-project-classifier-tool-agent.md`
- 계획 핵심:
  - `agent_slack/project_routing.py`를 추가해 `ProjectOption`, `ProjectRoutingDecision`, `ProjectRoutingResult`, `build_project_tools()`, `LangChainProjectRouterModel`을 정의한다.
  - LangChain `create_agent`와 `@tool` 기반 `list_registered_projects`, `score_project_candidates` tool을 사용한다.
  - `agent_slack` LangGraph에 `project_route` 노드를 추가해 `extract` 이후 후보별 프로젝트 선택, 프로젝트 요약, 연결 근거, 대체 후보, 사용자 확인 필요 여부를 붙인다.
  - Slack sync service가 DB 등록 프로젝트를 `process_daily_slack_sync(projects=...)`로 넘긴다.
  - Slack LLM project routing이 실행된 경우 기존 규칙 기반 `project_assignment` 중복 생성을 건너뛴다.
  - Review UI에는 `LLM 프로젝트 분류`, 프로젝트 연결 요약, 연결 근거를 표시한다.
- 계획서에는 TDD 단계, RED/GREEN 명령, Playwright 검증, 문서 갱신 범위를 포함했다.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 계획서 한글화 정리

- 사용자 요청에 맞춰 `docs/superpowers/plans/2026-05-15-slack-project-classifier-tool-agent.md`의 제목, 작업 단계, 대상 파일, 자체 검토 문구를 한글 중심으로 정리했다.
- LangChain `create_agent`와 tool-calling 구조는 유지하되, 문서상 안내 문구와 예시 프롬프트도 한국어 설명으로 맞췄다.
- 구현은 아직 진행하지 않았고, 현재 산출물은 작업 계획서와 진행 기록 갱신까지다.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 구현 - 작업 1, 2

- `backend/tests/test_agent_slack_project_routing.py`를 먼저 추가해 프로젝트 옵션, 후보 점수화 tool, fake project router 실행 계약을 정의했다.
- RED: `uv run pytest backend/tests/test_agent_slack_project_routing.py -q` 실행 시 `ModuleNotFoundError: No module named 'agent_slack.project_routing'`으로 실패하는 것을 확인했다.
- `agent_slack/project_routing.py`를 추가했다.
  - `ProjectOption`, `ProjectRoutingDecision`, `ProjectRoutingResult` 모델을 정의했다.
  - `list_registered_projects`, `score_project_candidates` LangChain tool을 생성하는 `build_project_tools()`를 추가했다.
  - `route_projects_for_candidates()`와 `LangChainProjectRouterModel` wrapper를 추가했다.
- GREEN: `uv run pytest backend/tests/test_agent_slack_project_routing.py -q` -> `3 passed`.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 구현 - 작업 3

- `backend/tests/test_agent_slack_pipeline_quality.py`에 `project_route` 노드 테스트를 추가했다.
- RED: `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py::test_agent_slack_applies_project_routing_to_candidates -q` 실행 시 `agent_slack.agent_slack`에 `route_projects_for_candidates`가 없어 실패하는 것을 확인했다.
- `agent_slack/agent_slack.py`에 다음을 추가했다.
  - `SlackAgentState.projects`, `project_router_model`, `project_prompt_tokens`, `project_completion_tokens`, `project_model_name`.
  - `project_route_node()`와 후보 payload/Slack source id 변환 helper.
  - `extract -> project_route -> END` LangGraph edge.
  - `process_daily_slack_sync(..., projects=..., project_router_model=...)` 인자.
- URL이 없는 후보의 fallback source id는 Python hash 대신 SHA-1 digest 기반으로 만들어 프로세스 간 안정성을 유지하도록 정리했다.
- GREEN: `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py::test_agent_slack_applies_project_routing_to_candidates -q` -> `1 passed`.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 구현 - 작업 4, 5

- `backend/tests/test_slack_agent_api.py`에 DB 등록 프로젝트 전달과 ReviewItem payload 보존 테스트를 추가했다.
- RED: `uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_project_routing_metadata_is_persisted -q` 실행 시 `process_daily_slack_sync()`에 전달된 `projects`가 빈 목록이라 실패했다.
- `backend/app/agents/slack_agent/sync_service.py`를 수정했다.
  - `projects` 테이블의 등록 프로젝트를 `project_key`, `name`, `summary` dict 목록으로 직렬화해 `agent_slack.process_daily_slack_sync(projects=...)`에 전달한다.
  - Slack Agent 후보의 `project_assignment_*` 필드를 `ReviewItem.payload`에 보존한다.
  - `AgentRun.metadata_.project_routing`에 활성화 여부, 방식, 프로젝트 수, 모델명, 프로젝트 라우팅 토큰 수를 기록한다.
- GREEN: `uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_project_routing_metadata_is_persisted -q` -> `1 passed`.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 구현 - 작업 6

- `backend/tests/test_mock_sync.py`에 Slack LLM project routing 활성 시 deterministic `project_assignment`를 만들지 않는 회귀 테스트를 추가했다.
- RED: `uv run pytest backend/tests/test_mock_sync.py::test_slack_llm_project_routing_skips_deterministic_project_assignments -q` 실행 시 `_connector_uses_slack_llm_project_routing` helper가 없어 실패했다.
- `backend/app/api/v1/integrations.py`에 `_connector_uses_slack_llm_project_routing()` helper를 추가했다.
- Slack sync에서 해당 helper가 true이면 기존 규칙 기반 `create_project_assignment_review_items()` 호출을 건너뛰도록 변경했다.
- 이후 조건을 좁혀 실제 Agent ReviewItem이 생성된 경우에만 deterministic project_assignment를 건너뛰도록 정리했다. provider key가 있어도 Agent 후보가 새로 생성되지 않은 no-op sync에서는 기존 프로젝트 fallback이 막히지 않는다.
- GREEN: `uv run pytest backend/tests/test_mock_sync.py::test_slack_llm_project_routing_skips_deterministic_project_assignments -q` -> `1 passed`.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 구현 - 작업 7

- `frontend/e2e/review-project-routing.spec.ts`를 추가해 Review 카드가 LLM 프로젝트 분류 요약과 연결 근거를 표시하는지 검증했다.
- RED:
  - sandbox 기본 실행은 Playwright Chromium `spawn EPERM`으로 막혀 권한을 올려 재실행했다.
  - `npm.cmd run test:visual -- review-project-routing.spec.ts --project=chromium-desktop` 실행 시 `LLM 프로젝트 분류` 문구를 찾지 못해 실패했다.
- `frontend/src/app/review/page.tsx`에 `projectRoutingLabel`, `projectRoutingSummary`, `projectRoutingReason` helper와 표시 블록을 추가했다.
- GREEN: `npm.cmd run test:visual -- review-project-routing.spec.ts --project=chromium-desktop` -> `1 passed`.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 구현 - 작업 8

- `backend/tests/test_project_memory_api.py`에 승인된 Slack LLM project routing 항목이 프로젝트 타임라인에 연결되는 회귀 테스트를 추가했다.
- 실행: `uv run pytest backend/tests/test_project_memory_api.py::test_approved_slack_llm_project_routing_item_appears_in_project_timeline -q`.
- 결과: `1 passed`.
- 해석: 새 `project_assignment_method=llm_tool` payload가 기존 Review 승인/프로젝트 활동 표시 경로와 호환된다.

## 2026-05-15 Slack Agent LangGraph 문서 작성

- `agent_slack/slack_agent_langgraph.md`를 추가했다.
- 현재 `agent_slack/agent_slack.py` 기준 LangGraph 흐름을 문서화했다.
  - `START -> preprocess -> classify -> summarize -> extract -> project_route -> END`.
  - 업무 신호가 없으면 `classify`에서 바로 `END`로 종료된다.
  - `project_route`는 등록 프로젝트와 후보가 있을 때만 LangChain tool-calling router를 실행한다.
- 문서에는 상태 모델, 노드별 역할, DB 저장 경계, 비용/안전 경계, 현재 주의점을 포함했다.

## 2026-05-15 Slack 프로젝트 분류 Tool Agent 통합 검증

- 백엔드 회귀:
  - `uv run pytest backend/tests/test_agent_slack_project_routing.py backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q` -> `60 passed`.
- Ruff:
  - 첫 실행에서 import 정렬 1건 자동 수정.
  - 재실행: `uv run ruff check ...` -> `All checks passed!`.
- 프론트엔드:
  - `npm.cmd exec tsc -- --noEmit` -> passed.
  - `npm.cmd run lint` -> passed.
  - `npm.cmd run build` -> passed.
  - `npm.cmd run test:visual -- review-project-routing.spec.ts` -> desktop/mobile `2 passed`.
- Ruff 자동 수정 이후 백엔드 회귀 묶음을 재실행했고 다시 `60 passed`를 확인했다.
- fallback source id 안정화 후 `agent_slack.py` ruff 재검사와 관련 단위 테스트 `5 passed`, 전체 관련 백엔드 회귀 `60 passed`를 다시 확인했다.

## 2026-05-15 Slack 동기화 장시간 실행 실패 오인 원인 확인 및 수정

- 증상: Slack 동기화 진행 중 화면에서 `동기화 실패`로 표시될 수 있다고 보고됐다.
- Playwright 실제 로컬 확인:
  - 로그인 후 `/integrations`에서 Slack 동기화 버튼을 클릭했다.
  - 최신 테스트 job `slack-34e086b550e64dcb94b75072f87577b6`은 `complete`로 끝났다.
  - runtime status는 `last_error=null`, message는 `fetched=0 created_review_items=5 skipped_events=0 pending_review_items=13`이었다.
  - 이번 실제 테스트로 검토 대기 수가 8개에서 13개로 늘었다.
- 원인:
  - 이전 대량 sync job은 `created_at=2026-05-15T01:08:02Z`, `updated_at=2026-05-15T01:10:34Z`로 약 153초 걸렸다.
  - 프론트 polling 한도는 `90 * 1.5초 = 135초`라, 백엔드가 정상 처리 중이어도 프론트가 먼저 timeout을 error로 처리했다.
  - 이 timeout error가 모달 제목에서 `Slack 동기화 실패`로 표시됐다.
- 수정:
  - 장시간 running 상태는 실패가 아니라 `백그라운드에서 계속 진행 중입니다...` 안내로 표시하도록 변경했다.
  - 120초 이상 진행 중이면 모달이 백그라운드 진행 안내로 전환된다.
  - polling 한도를 넘긴 경우에도 error 상태가 아니라 running/backgrounded 상태로 유지한다.
- 검증:
  - 신규 Playwright 회귀 테스트 `Slack sync polling timeout stays in background-running state instead of failure` 추가.
  - RED: 해당 문구가 없어 실패.
  - GREEN: `npm.cmd run test:visual -- integration-sync-modal.spec.ts --project=chromium-desktop -g "polling timeout"` -> `1 passed`.
  - 전체 모달 회귀: `npm.cmd run test:visual -- integration-sync-modal.spec.ts` -> desktop/mobile `6 passed`.
  - `npm.cmd exec tsc -- --noEmit`, `npm.cmd run lint`, `npm.cmd run build` 통과.

## 2026-05-15 Slack 동기화 실패 오인 방지 수정 완료

- 목표: Slack 동기화가 백엔드에서는 완료되었지만 긴 POST 응답이 끊겨 프론트에서 `Internal Server Error`로 표시되는 문제를 줄였다.
- 백엔드 변경:
  - `/api/v1/integrations/{connector_type}/sync` 요청 body에 `run_async` 옵션을 추가했다.
  - `run_async=true`일 때 즉시 `queued` 상태의 `SyncJob`을 만들고 같은 `job_id`로 백그라운드 동기화를 이어서 실행한다.
  - 기존 동기식 호출은 그대로 유지해 기존 테스트/계약과 호환되도록 했다.
  - `runtime-status.latest_sync`에 `created_at`, `updated_at`을 추가해 프론트가 방금 시작한 job인지 판정할 수 있게 했다.
  - `sync_connector_events()`는 외부에서 전달한 `job_id`를 재사용할 수 있게 했다.
- 프론트 변경:
  - Slack sync 버튼은 이제 `run_async=true`로 호출한다.
  - 응답이 `queued`/`running`이면 runtime-status를 polling해 실제 완료/실패를 판정한다.
  - POST 응답이 `Internal Server Error`, socket/network 계열로 끊겨도 runtime-status에서 방금 완료된 job을 찾으면 성공 완료 상태로 복구한다.
  - 완료 모달은 job message의 `pending_review_items`를 우선 사용해 최종 검토 대기 수치를 표시한다.
  - 모바일에서 완료 모달 하단 버튼이 겹쳐 `닫기` 클릭이 가로막히던 문제를 `max-height`, `overflow-y-auto`, 모바일 단일 열 버튼 배치로 수정했다.
- 회귀 테스트:
  - Playwright: `integration-sync-modal.spec.ts`
    - queued 응답 후 runtime-status 완료를 기다리는 정상 경로
    - POST 500 응답 유실 후 runtime-status 완료로 복구하는 경로
    - desktop/mobile 모두 통과
  - Backend:
    - async queued sync 응답
    - runtime-status timestamp 노출
    - sync/status/audit/connector 계약 회귀 묶음 통과
- 검증:
  - `npm.cmd run test:visual -- integration-sync-modal.spec.ts` -> 4 passed
  - `npm.cmd exec tsc -- --noEmit` -> passed
  - `npm.cmd run lint` -> passed
  - `npm.cmd run build` -> passed
  - `uv run pytest backend/tests/test_mock_sync.py backend/tests/test_integration_runtime_status.py backend/tests/test_stream.py backend/tests/test_audit_logs.py -q` -> 22 passed
  - `uv run pytest backend/tests/test_connector_ingestion_contract.py backend/tests/test_slack_agent_api.py backend/tests/test_mail_document_agent_api.py -q` -> 25 passed

## Task 1 - Baseline and Plan Review

- Started from `docs/superpowers/plans/2026-05-14-project-timeline-visibility.md`.
- Confirmed current checkout is a normal repo checkout on branch `agent_slack`, not a linked worktree.
- Current `git status --short` initially showed only the newly added plan file as untracked.
- Read the active Mail/Document bridge tests, RAG indexing tests, RAG indexing implementation, Mail/Document agent implementation, and Mail/Document service implementation.
- Important current-code adjustment: `backend/app/rag/indexing.py` already imports `ReviewItem`, so the previously reported `NameError` is no longer present in the checked-out code. The remaining RAG work is to preserve `source_ids` in Mail/Document ReviewItems and align tests with approval-based source chunk indexing.
- Initial sandboxed pytest was blocked by the uv-managed Python path. Re-running the targeted command outside the sandbox worked.
- Verification:
  - `uv run pytest backend/tests/test_mail_document_agent_review_bridge.py::test_mail_document_agent_bridge_filters_sources_and_persists_run -q` -> 1 passed.
  - `uv run pytest backend/tests/test_rag_indexing.py::test_build_rag_index_documents_includes_chunks_and_approved_knowledge -q` -> failed because current approval-only RAG policy excludes an unapproved chunk; this is an old expectation mismatch, not the prior `ReviewItem` NameError.
- Next task: add failing project timeline regression tests before changing production code.

## Task 2 - Project Timeline Direct Project-Key Regression

- Added `test_projects_api_links_approved_timeline_by_project_key_without_assignment` to `backend/tests/test_project_memory_api.py`.
- RED verification:
  - `uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_links_approved_timeline_by_project_key_without_assignment -q` -> failed with `StopIteration` because `/api/v1/projects` did not return the `seed-ir` project from a `TimelineEvent.project_key` alone.

## Task 3 - Preserve Project Key in Project Timeline Records

- Updated `backend/app/projects/service.py` to carry approved memory record project keys into `ProjectTimelineItem` values by mapping approved knowledge record ids back to their `project_key`.
- Chose this minimal approach because the file contains existing mojibake Korean string literals; it avoids broad text churn while fixing the matching behavior.
- GREEN verification:
  - `uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_links_approved_timeline_by_project_key_without_assignment -q` -> 1 passed.

## Task 4 - Review Approval to Project Timeline Regression

- Added `test_approved_review_item_with_project_key_appears_in_project_timeline` to prove a pending `timeline_event` ReviewItem with `payload.project_key` appears under the matching project after approval.
- Verification:
  - `uv run pytest backend/tests/test_project_memory_api.py::test_approved_review_item_with_project_key_appears_in_project_timeline -q` -> 1 passed.

## Task 5 - Keep Approved Knowledge Out of Connector Evidence

- Added `test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence`.
- RED verification:
  - The test first failed because an approved `history_event` was counted as connector evidence (`evidence_count == 1`).
- Updated `backend/app/projects/service.py` so connector evidence is built only from approved `project_assignment` items, while approved knowledge ReviewItems remain available for project timeline linking.
- Adjusted the test expectation to allow the existing promotion behavior where approving a `history_event` creates both `HistoryEvent` and mirror `TimelineEvent` records.
- GREEN verification:
  - `uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence -q` -> 1 passed.
  - `uv run pytest backend/tests/test_project_memory_api.py -q` -> 8 passed.

## Task 6 - Preserve Mail/Document Source Identity for RAG

- Added assertions to `test_mail_document_agent_bridge_filters_sources_and_persists_run` proving generated ReviewItems preserve:
  - `payload.source_ids`
  - `payload.source_types`
  - `payload.source_urls`
  - `payload.source_authors`
- RED verification:
  - The targeted bridge test failed with `KeyError: 'source_ids'`.
- Updated `backend/app/agents/mail_document_agent/service.py` to derive source identity metadata from the evidence packet and store it in each generated ReviewItem payload.
- Added `_unique_strings()` to preserve order while removing duplicate/blank values.
- GREEN verification:
  - `uv run pytest backend/tests/test_mail_document_agent_review_bridge.py::test_mail_document_agent_bridge_filters_sources_and_persists_run -q` -> 1 passed.
  - `uv run pytest backend/tests/test_mail_document_agent_review_bridge.py -q` -> 6 passed.

## Task 7/8 - RAG Approval-Based Source Chunk Indexing

- Confirmed `backend/app/rag/indexing.py` already imports `ReviewItem`; no production import change was needed.
- Updated `backend/tests/test_rag_indexing.py` so chunk indexing expectations match the approval-only policy:
  - Source chunks enter RAG only when their external `Source.source_id` appears in an approved `ReviewItem.payload.source_ids`.
  - Approved knowledge records still enter RAG through the existing approved knowledge path.
  - Unapproved synced chunks stay out of the RAG index by default.
- Added/updated tests to cover approved source chunks, unapproved source exclusion, parser metadata, parser status counts, dry-run summaries, budget reporting, job summaries, and indexing summaries under the approval-only policy.
- Verification:
  - `uv run pytest backend/tests/test_rag_indexing.py::test_build_rag_index_documents_includes_chunks_and_approved_knowledge backend/tests/test_rag_indexing.py::test_build_rag_index_documents_excludes_unapproved_source_chunks -q` -> 2 passed.
  - `uv run pytest backend/tests/test_rag_indexing.py -q` -> 25 passed.

## Task 9/10 - Frontend Project Timeline Items

- Updated `frontend/src/lib/api/types.ts` so `ProjectTimelineItem` includes optional `project_key`.
- Replaced `frontend/src/app/projects/page.tsx` with a clean Korean implementation because the existing file contained mojibake string literals that made safe partial patching unreliable.
- The project page now merges:
  - connector assignment evidence from `memory.evidence`
  - approved workflow items from `memory.timeline_items`
- Approved workflow items appear as completed tasks and are visually distinct from source evidence in the Gantt view.
- Verification:
  - `npm.cmd exec tsc -- --noEmit` from `frontend` -> passed.

## Task 11 - Targeted End-to-End Verification

- Ran the targeted backend suite for the changed approval, project timeline, Mail/Document bridge, and RAG indexing paths.
- Verification:
  - `uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_rag_indexing.py -q` -> 44 passed.
  - `npm.cmd exec tsc -- --noEmit` from `frontend` -> passed.
  - `npm.cmd run build` from `frontend` -> passed.

## Task 12 - Documentation

- Updated `docs/portfolio-log.md` with the approved project timeline and RAG visibility fix.
- Updated `docs/superpowers/runbooks/session-handoff.md` with continuation notes, verification evidence, and the distinction between this targeted fix and unrelated broader backend suite failures.
- Reverted generated `frontend/next-env.d.ts` churn caused by `npm.cmd run build`; it was unrelated to this work.
- Final hygiene:
  - `npm.cmd exec tsc -- --noEmit` from `frontend` after reverting generated churn -> passed.
  - `git diff --check` -> passed.

## 작업 13 - Slack 동기화 ReviewItem LLM 동작 진단

- Slack 동기화 후 `review_items`에 `Redis 큐 관련 결정사항 추출됨` 1건만 생성되는 이유를 확인했다.
- 현재 Slack 동기화 API는 변경된 Slack `Source`를 저장한 뒤
  `backend/app/api/v1/integrations.py`의 `_run_connector_agent_review()`에서
  `create_slack_agent_review_items(... SlackAgent(model=DeterministicSlackAgentModel()) ...)`를 호출한다.
- `Redis 큐 관련 결정사항 추출됨` 제목은 `backend/app/agents/slack_agent/agent.py`의 결정론 로컬 모델에서 나오는 하드코딩된 데모/스모크 결과이며, 실제 LLM 실행 결과가 아니다.
- 현재 실행 중인 Docker/Postgres 상태를 확인했다.
  - Slack `sources`: 195건
  - `review_items`: 1건
  - 해당 ReviewItem의 `agent_run_id`: 61
  - 해당 AgentRun의 `source_window`: `sync:slack:changed`
  - 해당 AgentRun의 `model_name`: `fake-slack-agent-model`
- 이전에 생성된 `slack_agent_v2` AgentRun 중 `gpt-4o-mini`를 사용한 기록은 존재하지만, 현재 Slack sync 버튼이 타는 활성 경로는 `agent_slack`의 LLM 파이프라인과 연결되어 있지 않다.
- 결론: 이번 증상은 sync 중 LLM이 실패해서 fallback 된 것이 아니라, 현재 sync 코드가 자동 ReviewItem 생성에 결정론/fake Slack Agent를 사용하기 때문에 발생한다. 이 모델은 실행 1회당 후보 1개를 반환하므로 ReviewItem도 1개만 생성된다.

## 작업 14 - Slack sync와 agent_slack LLM 파이프라인 연결

- `agent_slack` 폴더의 실제 실행 진입점인 `process_daily_slack_sync()`와 이를 DB에 저장하는
  `backend/app/agents/slack_agent/sync_service.py`의 `trigger_slack_agent_analysis()`를 확인했다.
- 기존에는 이 서비스가 존재했지만 `/api/v1/integrations/slack/sync`에서 호출되지 않아,
  sync 버튼은 항상 `DeterministicSlackAgentModel` 기반 ReviewItem만 생성했다.
- `trigger_slack_agent_analysis()`가 `source_ids`를 받을 수 있게 수정했다.
  - Slack sync가 방금 변경된 `Source.source_id`만 넘기도록 하기 위해서다.
  - 기존처럼 최근 N일 전체를 다시 분석하면 중복 비용과 중복 ReviewItem이 생길 수 있다.
- Slack sync 경로를 다음처럼 연결했다.
  - 운영형 local/prod 모드(`PARAWORKS_DEMO_MODE=false`)
  - provider key가 있는 경우
  - `agent_slack` LLM 파이프라인으로 변경된 Slack source만 분석
  - demo/test 모드 또는 provider key가 없는 경우 기존 결정론 스모크 경로 유지
- 테스트에서는 live LLM을 호출하지 않도록 `process_daily_slack_sync()`를 fake 함수로 대체했다.
- 검증:
  - `uv run pytest backend/tests/test_slack_agent_api.py::test_slack_sync_uses_agent_slack_llm_pipeline_when_provider_key_exists -q` -> 1 passed
  - `uv run pytest backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py backend/tests/test_integration_runtime_status.py::test_sync_returns_configuration_error_when_connector_is_not_configured -q` -> 8 passed
  - `uv run ruff check backend/app/api/v1/integrations.py backend/app/agents/slack_agent/sync_service.py backend/tests/test_slack_agent_api.py` -> passed
  - `uv run pytest backend/tests/test_slack_agent_review_bridge.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_api.py backend/tests/test_mock_sync.py -q` -> 23 passed

## 작업 15 - 사용자 정의 프로젝트 목록 및 분류 흐름 수정

- Gemini가 추가한 `projects` 테이블, `/api/v1/projects/define`, `/api/v1/projects/defined` 흐름을 이어받아 현재 상태를 확인했다.
- 문제 원인:
  - 프로젝트 생성 API는 있었지만, 분류 로직은 여전히 하드코딩 프로젝트 목록을 전제로 삼고 있었다.
  - `/api/v1/projects/defined`도 하드코딩 프로젝트와 DB 프로젝트를 합치도록 작성되어 있어 사용자가 요청한 방향과 맞지 않았다.
  - DB에 저장된 프로젝트가 없어도 이전 restart 과정에서 로컬 DB가 초기화되어 화면에 표시할 프로젝트가 없었다.
- 수정 내용:
  - `/api/v1/projects/defined`는 DB에 저장된 사용자 정의 프로젝트만 반환하도록 변경했다.
  - `/api/v1/projects`는 DB에 저장된 프로젝트를 evidence/timeline이 없어도 반환한다.
  - `build_project_assignment_candidates()`는 이제 하드코딩 프로젝트가 아니라 DB의 `Project.name`과 `Project.summary`를 기준으로 Slack/Gmail/Drive/Calendar source를 분류한다.
  - 승인된 과거 항목에 DB 프로젝트 행이 없더라도 `ReviewItem.payload.project_name`이 있으면 프로젝트 표시명으로 사용한다.
  - Review 화면의 프로젝트 선택 흐름은 `/api/v1/projects/defined` 목록을 사용하므로, 사용자가 LLM 제안값을 그대로 승인하거나 직접 프로젝트를 고른 뒤 저장/승인할 수 있다.
- 검증:
  - `uv run pytest backend/tests/test_project_memory_api.py -q` -> 12 passed
  - `uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q` -> 26 passed
  - `uv run ruff check backend/app/api/v1/projects.py backend/app/projects/service.py backend/app/projects/classifier.py backend/app/models/knowledge.py backend/tests/test_project_memory_api.py` -> passed
  - `cd frontend && npm.cmd exec tsc -- --noEmit` -> passed
  - `cd frontend && npm.cmd run build` -> passed

## 작업 16 - 동기화 후 검토사항 미생성 및 프로젝트 설명 깨짐 수정

- 사용자 제보:
  - 동기화 버튼을 눌렀는데 검토사항으로 넘어오는 항목이 보이지 않았다.
  - 프로젝트 생성 후 설명 뒤에 `?꾩쭅 ?뱀씤???꾨줈?앺듃 evidence...` 같은 깨진 문자열이 붙었다.
- 원인 확인:
  - 프로젝트 생성 API는 `projects` 테이블에 프로젝트만 저장했고, 이미 동기화된 Slack/Gmail/Drive/Calendar 소스를 새 프로젝트 기준으로 다시 분류하지 않았다.
  - 동기화 API는 변경된 source가 있을 때 Slack/Mail-Document Agent 후보는 만들 수 있었지만, 사용자 정의 프로젝트와 source를 연결하는 `project_assignment` 후보 생성은 별도 `/api/v1/projects/reclassify` 호출에만 의존했다.
  - `backend/app/projects/service.py`와 `backend/app/projects/classifier.py`에 깨진 한글 문자열이 남아 프로젝트 요약, 근거 사유, fallback 이름에 그대로 노출됐다.
- 수정 내용:
  - `/api/v1/projects/define`이 프로젝트 저장 직후 기존 source를 사용자 정의 프로젝트 기준으로 분류하고, 매칭되면 `project_assignment` ReviewItem을 `pending_review` 상태로 생성하도록 연결했다.
  - `/api/v1/integrations/{connector_type}/sync`가 source 저장 뒤 프로젝트 분류기도 실행해, 새로 동기화된 데이터와 이미 동기화되어 skipped 된 기존 데이터 모두 프로젝트 연결 검토사항으로 들어오도록 했다.
  - 프로젝트 요약, 승인 근거 문구, fallback 프로젝트명, Gmail 첨부 라벨, 프로젝트 분류 사유의 깨진 문자열을 읽을 수 있는 한국어로 교체했다.
  - 프로젝트명/설명 기반 분류에서 한국어 토큰 범위를 `가-힣`로 정리해 사용자 정의 한국어 프로젝트명도 안정적으로 매칭되게 했다.
- 검증:
  - `uv run pytest backend/tests/test_project_memory_api.py::test_define_project_returns_readable_empty_summary backend/tests/test_project_memory_api.py::test_define_project_creates_pending_assignment_candidates_from_existing_sources -q` -> 2 passed
  - `uv run pytest backend/tests/test_mock_sync.py::test_sync_creates_project_assignment_review_items_for_defined_projects -q` -> 1 passed
  - `uv run pytest backend/tests/test_mock_sync.py::test_duplicate_sync_still_classifies_existing_sources_for_new_project backend/tests/test_slack_agent_api.py::test_slack_sync_uses_agent_slack_llm_pipeline_when_provider_key_exists -q` -> 2 passed
  - `uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_mock_sync.py backend/tests/test_slack_agent_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q` -> 37 passed
  - `uv run ruff check backend/app/api/v1/projects.py backend/app/api/v1/integrations.py backend/app/projects/service.py backend/app/projects/classifier.py backend/tests/test_project_memory_api.py backend/tests/test_mock_sync.py` -> passed
  - `cd frontend && npm.cmd exec tsc -- --noEmit` -> passed
  - `cd frontend && npm.cmd run build` -> passed

## 작업 17 - Review/Project/Timeline 개선 작업계획서 작성

- 사용자가 제시한 8개 개선 사항을 기준으로 현재 코드 구조를 다시 확인했다.
- 확인한 핵심 문제:
  - Slack 업무 내용 판별이 짧은 의례 문구와 실제 업무 요청을 충분히 구분하지 못한다.
  - 프로젝트 분류가 부분 문자열에 약해 `유치원` 같은 단어를 `투자 유치` 프로젝트로 오인할 수 있다.
  - 타임라인/프로젝트 API가 승인 지식의 project key까지 탭 후보로 확장할 수 있어 “등록 프로젝트만 표시” 요구와 충돌한다.
  - History/Todo 승인 시 생성되는 mirror `TimelineEvent`와 원본 승인 지식이 함께 표시되면 같은 근거가 2개처럼 보일 수 있다.
  - Review 화면은 pending 항목 전체를 한 번에 가져오고 모든 promotion preview를 즉시 호출해 200개 항목에서 느려질 가능성이 높다.
  - Review 상단 bulk approve/reject와 카드 단위 빠른 프로젝트 선택 흐름이 아직 부족하다.
- 신규 계획 문서 작성:
  - `docs/superpowers/plans/2026-05-14-review-project-timeline-quality.md`
- 계획서에는 다음 작업 순서를 반영했다.
  - Slack 업무 신호 게이트 강화
  - 프로젝트 substring 오탐 제거
  - 타임라인 탭 등록 프로젝트 기준 정리
  - 승인 지식/타임라인 표시 중복 제거
  - Review 프로젝트 선택 UI/API 보강
  - Review 모두 승인/모두 반려 추가
  - Review 200개 렌더링 병목 완화
  - 프로젝트 탭 “승인된 활동” 문구와 역할 정리
- 이번 단계는 계획서 작성만 수행했으며, 프로덕션 코드는 변경하지 않았다.

## 작업 18 - 개선 작업 기준 테스트 실행

- `superpowers:executing-plans`, `superpowers:test-driven-development`, `superpowers:using-git-worktrees` 흐름을 확인하고 현재 `agent_slack` 브랜치에서 작업을 시작했다.
- 현재 작업공간은 일반 checkout이지만 이미 `agent_slack` 기능 브랜치에 있으므로 별도 worktree를 만들지 않고 현재 브랜치에서 진행한다.
- 기준 테스트 실행:
  - `uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_api.py -q`
  - 결과: `41 passed`
- 첫 실행은 샌드박스가 사용자 프로필 아래 Python 실행 파일 생성을 막아 실패했으며, 승인된 외부 실행으로 재시도해 정상 통과했다.
- 다음 단계는 Slack 업무 신호 게이트와 프로젝트 부분 문자열 오탐 방지 테스트를 먼저 추가하는 것이다.

## 작업 19 - Slack 업무 신호 게이트와 프로젝트 오탐 방지 구현

- 실패 테스트를 먼저 추가했다.
  - `부탁드립니다.` 단독 문장은 `low_context_request`로 제외된다.
  - `금요일까지 정산 파일 검토 부탁드립니다.`는 업무 대상/행동/기한 신호가 있어 포함된다.
  - ranked Slack evidence packet은 `후...`, `부탁드립니다.`를 제외하고 실제 업무 메시지만 남긴다.
  - `투자 유치` 프로젝트는 `투자 유치원 등교 일정`에 부분 문자열로 매칭되지 않는다.
  - `투자 유치 전략 회의`는 정상적으로 해당 프로젝트 후보가 된다.
- 구현 내용:
  - `backend/app/agents/slack_agent/quality.py`를 추가해 Slack 메시지의 업무 신호를 deterministic하게 판별한다.
  - ranked Slack evidence 선정 단계에서 저신호 메시지를 제외하고, 업무 신호 점수를 ranking에 반영했다.
  - LLM prompt에는 단독 인사/반응/감탄/맥락 없는 부탁 문구를 제외하라는 요구사항을 추가했다.
  - `backend/app/projects/classifier.py`를 정리해 한글 token boundary 기반 alias 매칭을 적용했다.
  - `유치`, `투자`, `회의`, `일정`, `자료`처럼 단독으로 쓰이면 오탐 위험이 큰 term은 독립 alias에서 제외했다.
- 검증:
  - `uv run pytest backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py::test_project_classifier_does_not_match_phrase_inside_korean_word backend/tests/test_project_memory_api.py::test_project_classifier_matches_complete_korean_project_phrase -q` -> `5 passed`
  - `uv run pytest backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_review_bridge.py -q` -> `35 passed`
- 첫 관련 테스트 확장 시 `Postgres/pgvector 사용 결정` 문장이 너무 엄격하게 제외되어 `postgres`, `pgvector`, `비용`, `상한`, `사용` 신호를 보강했다.

## 작업 20 - 등록 프로젝트 기준 노출과 승인 활동 중복 표시 분리

- 실패 테스트를 먼저 조정/추가했다.
  - 승인된 `project_assignment`가 있어도 `projects` 테이블에 등록되지 않은 project key는 `/api/v1/projects`에 표시하지 않는다.
  - 등록된 프로젝트는 승인 근거가 없어도 계속 표시한다.
  - 승인된 `history_event`가 mirror `TimelineEvent`를 만들더라도 프로젝트 활동 목록에는 `history_event` 하나로 보이고, 타임라인 목록에는 `timeline_event` 성격만 남는다.
- 구현 내용:
  - `backend/app/projects/service.py`의 프로젝트 목록 기준을 승인 지식 project key가 아니라 `Project` 테이블로 제한했다.
  - 응답 구조에 `activity_items`를 추가했다.
  - `timeline_items`는 타임라인 표시용 항목으로 제한하고, `activity_items`는 승인된 결정/히스토리/할 일/타임라인 활동을 프로젝트별로 모은 목록으로 분리했다.
  - 같은 source/snippet/summary를 공유하는 mirror `timeline_event`는 활동 목록에서 dedupe한다.
  - `frontend/src/lib/api/types.ts`, `frontend/src/app/projects/page.tsx`, `frontend/src/app/timeline/page.tsx`를 새 응답 구조와 한국어 설명에 맞게 수정했다.
- 검증:
  - `uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_returns_approved_project_evidence_only backend/tests/test_project_memory_api.py::test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence backend/tests/test_project_memory_api.py::test_projects_api_hides_unregistered_approved_project_keys -q` -> `3 passed`
  - `uv run pytest backend/tests/test_project_memory_api.py -q` -> `17 passed`
  - `cd frontend && npm.cmd exec tsc -- --noEmit` -> passed

## 작업 21 - Review 프로젝트 선택, bulk 처리, pagination/lazy preview 구현

- 실패 테스트를 먼저 추가했다.
  - Review 목록 API가 `limit`, `offset`, `total_count`, `has_more`를 반환한다.
  - `PATCH /api/v1/review/{id}`에서 등록되지 않은 `project_key`는 거절하고, 등록 프로젝트를 선택하면 `project_name`을 서버가 보정한다.
  - `POST /api/v1/review/bulk`로 현재 항목들을 일괄 반려할 수 있다.
  - 일괄 승인은 승격 가능한 항목만 승인하고, 필수 필드가 부족한 항목은 `failed_items`에 담아 보고한다.
- 구현 내용:
  - `backend/app/schemas/review.py`에 `ReviewBulkActionRequest`를 추가했다.
  - `backend/app/api/v1/review.py`에 pagination metadata와 `/bulk` 엔드포인트를 추가했다.
  - Review payload의 프로젝트 변경 시 `projects` 테이블에 등록된 프로젝트인지 검증하도록 했다.
  - `frontend/src/app/review/page.tsx`는 초기 로딩 시 50개만 가져오고 모든 promotion preview를 즉시 호출하지 않는다.
  - preview는 그룹을 펼칠 때 해당 그룹 항목만 lazy load한다.
  - Review 탭 최상단에 “모두 승인”, “모두 반려” 버튼을 추가했다.
  - 각 Review 항목에 등록 프로젝트 select를 노출해 편집 모드에 들어가지 않아도 프로젝트를 지정할 수 있게 했다.
  - “더 보기” 버튼으로 다음 50개를 불러오도록 했다.
- 검증:
  - `uv run pytest backend/tests/test_review.py::test_patch_review_item_requires_registered_project_key backend/tests/test_review.py::test_review_list_supports_limit_offset_metadata backend/tests/test_review.py::test_bulk_reject_pending_review_items backend/tests/test_review.py::test_bulk_approve_reports_items_that_cannot_be_promoted -q` -> `4 passed`
  - `uv run pytest backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q` -> `20 passed`
  - `uv run pytest backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_project_memory_api.py -q` -> `37 passed`
  - `cd frontend && npm.cmd exec tsc -- --noEmit` -> passed

## 작업 22 - agent_slack 저신호 필터 연결 및 최종 검증

- `agent_slack.process_daily_slack_sync()` 경로에서도 저신호 Slack 메시지만 있는 경우 LLM work filter를 호출하지 않도록 테스트를 추가했다.
  - `backend/tests/test_agent_slack_pipeline_quality.py`
- `agent_slack/agent_slack.py`의 `classify_work_node()` 앞단에 `classify_slack_work_signal()`을 연결했다.
  - deterministic 업무 신호가 없는 메시지 묶음은 바로 `is_work_related=False`로 끝난다.
  - deterministic 필터를 통과한 메시지만 저비용 LLM 필터에 전달하고, 프롬프트에는 작성자와 최대 200자 본문을 함께 넣는다.
- Slack API 회귀 테스트 중 영어 mock seed가 너무 엄격하게 제외되는 문제가 있어 `redis`, `queue`, `review queue`, `evidence`, `confirm`, `verify` 등 영어 업무 신호를 추가했다.
- 문서 업데이트:
  - `docs/portfolio-log.md`
  - `docs/superpowers/runbooks/session-handoff.md`
- 최종 검증:
  - `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_review_bridge.py backend/tests/test_slack_agent_api.py -q` -> `25 passed`
  - `uv run ruff check agent_slack/agent_slack.py backend/app/agents/slack_agent backend/app/projects backend/app/api/v1/review.py backend/app/schemas/review.py backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py backend/tests/test_review.py` -> passed
  - `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_review_bridge.py backend/tests/test_slack_agent_api.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_mock_sync.py -q` -> `66 passed`
  - `cd frontend && npm.cmd exec tsc -- --noEmit` -> passed
  - `cd frontend && npm.cmd run build` -> passed
- `npm.cmd run build`가 생성한 `frontend/next-env.d.ts` 경로 변경은 구현과 무관한 빌드 산출물 변화라 원래 상태로 되돌렸다.

## 작업 23 - Slack 동기화 후 검토사항 빈 화면 원인 확인 및 인증 오류 표시 개선

- 사용자 증상:
  - Slack 동기화 후 검토사항 탭에 아무 데이터가 없는 것처럼 보임.
- 확인 결과:
  - Docker 기준 Postgres/Redis/Minio는 실행 중이었다.
  - Slack 런타임 상태와 DB 기준으로 Slack source 210개와 pending review 218개가 존재했다.
  - 인증 세션으로 `/api/v1/review?status=pending_review&limit=5`를 직접 호출하면 `total_count=218`이 반환됐다.
  - pending review 구성은 `history_event` 4개, `todo` 3개, `decision_record` 1개, `project_assignment` 210개였다.
  - 브라우저에서 미로그인 상태로 `/review`를 열면 Review API가 `401 Authentication required`를 반환하지만, 화면에 “대기 중인 검토 항목이 없습니다.”가 함께 표시되어 빈 데이터처럼 보였다.
- 조치:
  - `frontend/src/lib/api/client.ts`에서 API 오류 응답의 JSON `detail`을 사람이 읽기 쉬운 메시지로 변환하도록 수정했다.
  - `frontend/src/app/review/page.tsx`에서 인증 오류가 있을 때 로그인 안내와 `/login` 링크를 표시하도록 수정했다.
  - 오류가 있을 때는 빈 상태 메시지를 숨기도록 수정했다.
- 검증:
  - `cd frontend && npm.cmd exec tsc -- --noEmit` -> passed
  - 브라우저 미로그인 상태에서 `/review`는 `/login`으로 이동하며 빈 검토 목록 메시지를 표시하지 않는 것을 확인했다.
  - 브라우저에서 `admin@paraworks.com` 로컬 로그인 후 `/review`에 `검토사항 218`, `50/218개 로드`, `paraworks MVP구축 source 연결` 그룹이 표시되는 것을 확인했다.

## 작업 24 - `굿굿` 같은 저신호 Slack reply가 프로젝트 업무 후보로 올라오는 원인 수정

- 사용자 증상:
  - 검토사항 상세 내용에 `굿굿`처럼 의미 없는 반응이 업무 내용처럼 표시됨.
- 원인 확인:
  - 실제 DB에서 `ReviewItem` id 518이 `project_classifier`가 만든 `project_assignment` 항목으로 확인됐다.
  - 해당 항목은 Slack Agent의 업무 후보가 아니라 프로젝트 자동 연결 후보였다.
  - 프로젝트 설명의 `slack`, `gmail`, `google drive`, `data`, `timeline` 같은 일반 매체 단어가 alias로 등록되어 Slack source 대부분이 프로젝트 후보로 잡힐 수 있었다.
  - Slack thread reply source의 실제 reply는 `굿굿`뿐인데, parent context와 일반 alias 매칭 때문에 `project_assignment`가 생성됐다.
- 실패 테스트:
  - `backend/tests/test_project_memory_api.py::test_project_classifier_ignores_generic_connector_terms_and_low_signal_slack_reply`
  - 기대: 프로젝트 설명에 Slack/Gmail/Drive가 있어도 `Thread reply: 굿굿` source는 후보가 되면 안 됨.
  - 최초 실행 결과: 해당 source가 `ProjectAssignmentCandidate`로 생성되어 실패.
- 조치:
  - `backend/app/projects/classifier.py`에서 `slack`, `gmail`, `google`, `drive`, `data`, `timeline`, `source` 같은 일반 connector/매체 단어를 프로젝트 alias에서 제외했다.
  - Slack source는 프로젝트 후보로 만들기 전에 실제 메시지 텍스트가 `classify_slack_work_signal()`을 통과하는지 확인하도록 했다.
  - `Thread parent: ... Thread reply: ...` 형태에서는 프로젝트 후보 판단용 업무 신호를 reply 본문 기준으로 본다.
- 검증:
  - `uv run pytest backend/tests/test_project_memory_api.py -q` -> `18 passed`
  - `uv run pytest backend/tests/test_mock_sync.py backend/tests/test_slack_agent_quality.py -q` -> `7 passed`
  - `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_review_bridge.py backend/tests/test_slack_agent_api.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_mock_sync.py -q` -> `67 passed`
  - `uv run ruff check backend/app/projects/classifier.py backend/tests/test_project_memory_api.py` -> passed
  - 실제 DB의 `ReviewItem` id 518 source를 새 분류 정책으로 재분류하면 후보가 `None`으로 떨어지는 것을 확인했다.
  - 현재 DB의 pending `project_assignment` 160개 중 새 정책으로도 유지될 항목은 5개, 예전 넓은 alias 매칭으로 생성된 항목은 155개로 확인했다.
- 주의:
  - 이번 수정은 새 동기화/재분류에서 같은 오탐이 다시 생성되지 않게 막는다.
  - 이미 생성된 pending review 항목은 DB에 남아 있으므로, 기존 `굿굿` 항목은 UI에서 반려하거나 별도 정리 작업으로 제거해야 한다.
## 작업 25 - Slack sync 후 ReviewItem 복구 누락 및 검토사항 첫 화면 정렬 수정

- 사용자 증상:
  - DB 데이터를 수동 삭제하고 Slack 동기화를 다시 눌렀는데 검토사항에 안 보임.
- 원인 확인:
  - 코드 파일 기준으로는 `굿굿` 오탐 방지 수정이 들어갔지만, 실행 중인 백엔드는 이전 프로세스라 `/api/v1/projects/reclassify?dry_run=true`가 여전히 `candidate_count=210`을 반환했다.
  - `scripts/paraworks-docker.ps1`로 백엔드/프론트 서버를 재시작한 뒤 같은 API가 `candidate_count=5`를 반환해 새 코드 반영을 확인했다.
  - 별도 구조 문제도 확인했다. ReviewItem만 수동 삭제하고 Slack source는 남아 있으면 다음 sync는 duplicate source로 처리되어 `changed_source_ids=[]`가 되고, 기존 코드가 Slack Agent review 후보를 재생성하지 않았다.
  - 또한 Review 목록은 최신순만 사용해 새로 생성된 `project_assignment`가 첫 50개를 채우면서 실제 Slack Agent 후보 7개가 뒤로 밀렸다.
- 실패 테스트:
  - `backend/tests/test_mock_sync.py::test_duplicate_slack_sync_recreates_agent_reviews_when_review_items_were_deleted`
    - ReviewItem만 삭제한 뒤 duplicate Slack sync가 agent review 후보를 복구해야 한다.
  - `backend/tests/test_review.py::test_review_list_prioritizes_knowledge_candidates_before_project_assignments`
    - Review 첫 페이지에서는 `decision_record`, `todo`, `history_event` 같은 지식 후보가 `project_assignment`보다 먼저 나와야 한다.
- 조치:
  - `backend/app/api/v1/integrations.py`에서 duplicate sync라도 해당 connector의 Agent ReviewItem coverage가 없으면 기존 source ids로 Agent review 생성을 복구하도록 했다.
  - 기존 rejected/approved/pending Agent ReviewItem이 하나라도 있으면 사용자의 검토 이력을 존중해 자동 재생성하지 않는다.
  - `backend/app/api/v1/review.py`에서 Review Queue 정렬 우선순위를 추가했다.
    - `decision_record` -> `todo` -> `history_event` -> `timeline_event` -> 기타 -> `project_assignment`
    - 같은 유형 안에서는 최신 id 우선.
- 서버 반영:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\paraworks-docker.ps1 -Stop`
  - `powershell -ExecutionPolicy Bypass -File .\scripts\paraworks-docker.ps1`
  - 재시작 후 backend/frontend 정상 응답 확인.
- 검증:
  - `uv run pytest backend/tests/test_mock_sync.py::test_duplicate_slack_sync_recreates_agent_reviews_when_review_items_were_deleted backend/tests/test_review.py::test_review_list_prioritizes_knowledge_candidates_before_project_assignments -q` -> `2 passed`
  - `uv run pytest backend/tests/test_mock_sync.py backend/tests/test_review.py backend/tests/test_project_memory_api.py backend/tests/test_slack_agent_api.py -q` -> `43 passed`
  - `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_review_bridge.py backend/tests/test_slack_agent_api.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_mock_sync.py -q` -> `69 passed`
  - `uv run ruff check backend/app/api/v1/integrations.py backend/app/api/v1/review.py backend/app/projects/classifier.py backend/tests/test_mock_sync.py backend/tests/test_review.py backend/tests/test_project_memory_api.py` -> passed

## 작업 26 - Playwright Chromium 설치 및 실행 확인

- 사용자 요청:
  - Slack 동기화/검토사항 UI 문제를 정확히 재현하기 전에 Playwright를 설치한다.
- 확인:
  - `frontend/package.json`에는 이미 `@playwright/test`와 `test:visual` 스크립트가 등록되어 있었다.
  - 이전 Playwright 오류는 npm 패키지 부재가 아니라 Chromium 브라우저 바이너리 부재/실행 권한 문제로 판단했다.
- 조치:
  - `frontend`에서 `npm.cmd exec playwright install chromium`을 실행해 Playwright Chromium 바이너리를 설치했다.
- 검증:
  - `npm.cmd exec -- playwright --version` -> `Version 1.59.1`
  - `npm.cmd run test:visual -- --list` -> 148개 테스트가 정상적으로 목록화됨.
  - 샌드박스 내부 headless launch는 Windows 권한 때문에 `spawn EPERM`이 발생했다.
  - 동일한 Chromium launch 검증을 승인된 외부 실행으로 재시도해 `chromium-launch-ok`를 확인했다.
- 주의:
  - 실제 Playwright 브라우저 실행 테스트는 샌드박스 밖 권한이 필요할 수 있다.
  - 실행 중인 서버에서 `/api/v1/projects/reclassify?dry_run=true` -> `candidate_count=5`
  - 실행 중인 서버에서 `/api/v1/review?status=pending_review&limit=10` 첫 항목 유형이 `decision_record`, `todo`, `history_event` 순으로 먼저 나오는 것을 확인했다.
  - 브라우저 `/review`에서 `검토사항 217`, `결정 기록`, `할 일`, `히스토리` 그룹이 첫 화면에 표시되는 것을 확인했다.

## 작업 27 - Slack sync 0건 원인 분리 및 user token connector 보강

- 사용자 증상:
  - 서버 재시작 후 Slack 동기화를 눌러도 검토사항에 새 항목이 보이지 않는다고 보고됨.
- Playwright 재현:
  - `admin@paraworks.com`으로 로그인한 뒤 `/integrations`에서 Slack 동기화 버튼을 클릭했다.
  - 동기화 응답은 `fetched_events=0`, `created_review_items=0`, `changed_source_ids=[]`였다.
  - 같은 세션에서 `/review`로 이동하면 검토사항 14개가 표시되고 빈 상태 문구는 표시되지 않았다.
- 원인 분리:
  - DB cursor 없이 현재 Slack connector를 직접 실행하면 최근 7일 이벤트 210개를 가져올 수 있었다.
  - 즉 현재 실행 환경의 Slack 접근 자체는 가능하다.
  - UI에서 누른 일반 sync가 0건인 이유는 DB에 이미 Slack source 210개가 있고, connector sync가 최신 source timestamp 이후의 변경분만 가져오는 incremental 정책을 따르기 때문이다.
  - 별도로 코드상 위험도 확인했다. 기존 `SlackConnector`는 설정된 channel id도 `conversations.list`의 bot membership 결과에 없으면 history 호출 전 단계에서 조용히 제외했다.
  - OAuth/direct-connect가 저장한 user token도 sync connector에 연결되지 않아 DM/user-token 접근 흐름이 실제 sync에서 활용되지 않았다.
- 실패 테스트:
  - `test_slack_connector_fetches_configured_channel_even_when_membership_list_is_empty`
  - `test_slack_connector_prefers_user_client_for_configured_channel_when_available`
  - `test_sync_connector_uses_installed_slack_user_token_when_available`
- 조치:
  - `SlackConnector`에 선택적 `user_client`를 추가했다.
  - 설정된 Slack channel id는 `conversations.list` membership 결과가 비어 있어도 history 조회를 시도하도록 했다.
  - user token이 있으면 설정 채널 조회에 user client를 우선 사용하고, Slack API 오류가 나면 bot client로 fallback한다.
  - installed Slack connection의 `local:slack:{workspace}:user` token을 찾아 sync connector에 연결했다.
- 검증:
  - 신규 회귀 테스트 3개 -> passed.
  - `uv run pytest backend/tests/test_slack_connector.py backend/tests/test_connector_factory.py backend/tests/test_mock_sync.py backend/tests/test_slack_agent_api.py -q` -> `35 passed`
  - `uv run pytest backend/tests/test_agent_slack_pipeline_quality.py backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_review_bridge.py backend/tests/test_slack_agent_api.py backend/tests/test_slack_connector.py backend/tests/test_connector_factory.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_mock_sync.py -q` -> `94 passed`
  - `uv run ruff check backend/app/connectors/slack.py backend/app/connectors/factory.py backend/tests/test_slack_connector.py backend/tests/test_connector_factory.py` -> passed
  - 서버 재시작 후 Playwright 실제 흐름 검증 -> `status=passed`, `review_total_count=14`
- 주의:
  - 현재 DB는 이미 Slack source 210개와 pending review 14개가 있어 일반 sync가 새 메시지를 만들지 않는 것이 정상이다.
  - DB에서 source까지 지운 초기 상태라면 이번 connector 보강으로 최근 7일 Slack 이벤트를 다시 가져올 수 있다.

## 작업 28 - Slack sync 원본 수집 후 ReviewItem 공백처럼 보이는 상태 수정

- 사용자 증상:
  - DB 데이터를 정리한 뒤 Slack 동기화를 실행하면 `sources`에는 Slack 원본이 들어오지만 `review_items`에는 데이터가 없는 것처럼 보였다.
- 원인:
  - `sync_connector_events()`가 Slack 원본 수집/ingestion만 끝난 시점에 `SyncJob.status='complete'`, `progress_pct=100`으로 먼저 커밋하고 있었다.
  - 그 뒤 `/api/v1/integrations/slack/sync` 라우트에서 Slack Agent LLM 분석과 프로젝트 분류 ReviewItem 생성을 이어서 실행한다.
  - 실제 DB 기준 최신 전체 동기화는 Slack source 210개를 먼저 저장했고, 약 2분 20초 뒤 ReviewItem 11개를 생성했다. 이 사이에는 Job이 complete처럼 보여 사용자가 “동기화는 끝났는데 review_items가 비었다”고 판단할 수 있었다.
- 조치:
  - connector ingestion이 끝난 뒤 Agent/프로젝트 ReviewItem 생성 단계로 넘어가면 SyncJob을 다시 `running`, `progress_pct=75`, `message='agent_review=running'` 상태로 표시하도록 수정했다.
  - Agent/프로젝트 ReviewItem 생성이 끝난 뒤에만 최종 `complete`, `progress_pct=100`으로 업데이트한다.
  - sync 응답에 `pending_review_count`를 추가해 “이번에 새로 생성된 ReviewItem 수”와 “현재 검토 대기 총량”을 구분할 수 있게 했다.
  - 통합 화면의 sync 결과 카드에 `새 검토 항목`과 `검토 대기`를 분리해 표시하도록 수정했다.
  - Slack 런타임 상태의 오류 조치 안내를 한국어로 정리했다.
- 검증:
  - 신규 회귀 테스트 `test_slack_sync_keeps_job_running_until_agent_reviews_are_persisted`를 추가했다.
  - RED 확인: 기존 코드는 Agent Review 생성 중에도 Job 상태가 `complete`라 테스트 실패.
  - GREEN 확인: 수정 후 신규 테스트 통과.
  - `uv run pytest backend/tests/test_mock_sync.py backend/tests/test_integration_runtime_status.py backend/tests/test_slack_agent_api.py backend/tests/test_audit_logs.py -q` -> `24 passed`
  - `uv run ruff check backend/app/api/v1/integrations.py backend/tests/test_mock_sync.py` -> passed
  - `npm.cmd exec tsc -- --noEmit` -> passed
  - `npm.cmd run build` -> passed
  - Playwright 실제 브라우저 검증:
    - `/integrations`에서 Slack 동기화 버튼 클릭
    - sync 응답: `created_review_items=0`, `pending_review_count=11`, `fetched_events=0`, `skipped_events=0`
    - `/api/v1/review?status=pending_review` 총량: `11`
    - 결과: sync 응답의 `pending_review_count`와 Review Queue 총량 일치.
- 현재 해석:
  - 현재 DB에는 이미 Slack source 210개와 pending ReviewItem 11개가 있으므로 일반 incremental sync는 새 이벤트가 없으면 `created_review_items=0`이 정상이다.
  - 앞으로는 긴 Slack Agent 분석 중에도 Job이 조기 complete로 보이지 않고, 동기화 결과에서 현재 검토 대기 총량을 바로 확인할 수 있다.

## 작업 29 - 동기화 진행 모달 UX 구현 시작

- 목표:
  - Slack/Gmail/Drive/Calendar 동기화 버튼을 누르면 동기화가 끝날 때까지 진행 모달을 띄운다.
  - 기본적으로 화면 뒤의 다른 작업을 막되, 오래 걸릴 때 사용자가 `백그라운드에서 계속 진행`을 선택하면 모달을 내릴 수 있게 한다.
  - 완료 후에는 새 검토 항목 수와 현재 검토 대기 총량을 명확히 보여준다.
- TDD RED:
  - `frontend/e2e/integration-sync-modal.spec.ts`를 추가했다.
  - 테스트는 Slack sync API 응답을 지연시키고, 클릭 직후 `sync-progress-modal`과 차단 배경이 나타나는지 확인한다.
  - 최초 실행 결과:
    - 샌드박스 기본 실행은 Chromium `spawn EPERM`으로 실패.
    - 권한 상승 후 실행 시 UI에 `sync-progress-modal`이 없어 테스트 실패.
  - 실패 원인은 현재 통합 화면이 버튼 텍스트만 `동기화 중`으로 바꾸고 별도 진행 모달/차단 배경을 렌더링하지 않기 때문이다.
- 구현:
  - `frontend/src/app/integrations/page.tsx`에 `SyncProgressModal`을 추가했다.
  - 동기화 시작 시 즉시 모달을 열고 `원본 수집과 AI 분석`, `프로젝트 분류`, `검토 항목 저장` 단계를 표시한다.
  - 모달이 열려 있는 동안 화면 뒤 작업은 차단된다.
  - 사용자가 오래 걸린다고 판단하면 `백그라운드에서 계속 진행`으로 모달만 내릴 수 있다. 이때 동기화 자체는 계속 진행된다.
  - 완료 후에는 `새 검토 항목 N개`, `검토 대기 N개`와 `검토사항으로 이동`, `닫기`를 표시한다.
- GREEN:
  - `npm.cmd run test:visual -- integration-sync-modal.spec.ts --project=chromium-desktop` -> `1 passed`
- 추가 검증:
  - `npm.cmd run test:visual -- integration-sync-modal.spec.ts` -> `2 passed` (desktop/mobile)
  - `npm.cmd exec tsc -- --noEmit` -> passed
  - `npm.cmd run lint` -> passed
  - `npm.cmd run build` -> passed
  - `uv run pytest backend/tests/test_mock_sync.py backend/tests/test_integration_runtime_status.py backend/tests/test_slack_agent_api.py backend/tests/test_audit_logs.py -q` -> `24 passed`
  - `uv run pytest backend/tests/test_mock_sync.py backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q` -> `48 passed`
  - 실제 로컬 서버 Playwright 검증:
    - Slack sync 클릭 시 진행 모달이 표시됨.
    - sync 응답 `created_review_items=0`, `pending_review_count=11`
    - Review API `total_count=11`
    - Slack source count `210`
    - 최신 sync message `fetched=0 created_review_items=0 skipped_events=0 pending_review_items=11`
    - `굿굿`, `후...`, `부탁드립니다` 저신호 문구가 pending ReviewItem 목록에 직접 포함되지 않음.

## 2026-05-15 검토사항 unknown 표시 원인 재현

- 요청: 검토사항 화면에서 `unknown`으로 보이는 항목을 Playwright로 확인하고 수정한다.
- Playwright 실제 화면 확인:
  - 로그인 후 `/review`를 열고 그룹을 펼쳤다.
  - 현재 pending review는 11개, 그룹은 8개로 확인됐다.
  - 화면 본문에서 `unknown`이 12회 표시됐다.
- 원인:
  - `project_classifier`가 만든 `project_assignment` 항목은 유료/LLM AgentRun 없이 deterministic 분류로 생성된다.
  - 해당 항목에는 `payload.prompt_version`, `payload.estimated_cost_usd`, `agent_run_id`가 없다.
  - 백엔드 응답의 기본 `agent_run_details`가 `model_name: "Unknown"`, `prompt_version: "Unknown"`으로 내려오고, 프론트는 payload 값이 없으면 Prompt/Cost에 `unknown`을 표시한다.
- 다음 작업:
  - Playwright 회귀 테스트를 먼저 추가해 deterministic project classifier 항목에서 `unknown`이 보이지 않아야 함을 고정한다.
  - UI에는 `규칙 기반 분류`, `LLM 미사용`처럼 사용자가 이해할 수 있는 문구를 표시한다.

## 2026-05-15 검토사항 unknown 표시 수정 완료

- TDD RED:
  - `frontend/e2e/review-agent-metadata.spec.ts`를 추가했다.
  - 테스트는 `project_classifier`가 만든 `project_assignment` 항목에 `agent_run_id`, `payload.prompt_version`, `payload.estimated_cost_usd`가 없어도 Review 화면이 `unknown`을 표시하지 않아야 함을 검증한다.
  - 최초 실행: `npm.cmd run test:visual -- review-agent-metadata.spec.ts --project=chromium-desktop` -> 실패. 기대한 `규칙 기반 분류` 문구가 없고 기존 UI가 `unknown`을 표시했다.
- 수정:
  - `frontend/src/lib/api/types.ts`에 `ReviewAgentRunDetails`를 추가하고 `ReviewItem.agent_run_details` 타입을 반영했다.
  - `frontend/src/app/review/page.tsx`에서 `Unknown` 문자열을 유효한 메타데이터로 취급하지 않도록 정규화했다.
  - `project_classifier`처럼 AgentRun 없이 생성되는 deterministic 검토 항목은 Prompt에 `규칙 기반 분류`, Cost에 `LLM 미사용`을 표시한다.
  - `backend/app/api/v1/review.py`는 AgentRun이 없는 항목의 기본 상세값을 `"Unknown"` 문자열 대신 `null`로 내려주도록 보정했다.
- 검증:
  - `npm.cmd run test:visual -- review-agent-metadata.spec.ts` -> `2 passed` (desktop/mobile)
  - `npm.cmd exec tsc -- --noEmit` -> passed
  - `uv run ruff check backend/app/api/v1/review.py` -> passed
  - `uv run pytest backend/tests/test_review.py -q` -> `15 passed`
  - `npm.cmd run lint` -> passed
  - `npm.cmd run build` -> passed
  - 실제 로컬 서버 Playwright 검증:
    - `/review`의 8개 그룹을 펼쳐 Prompt/Cost 타일 22개를 추출했다.
    - 메타데이터 타일 값 중 `unknown`은 0개였다.
    - `규칙 기반 분류`, `LLM 미사용` 문구가 실제 화면에 표시됐다.
    - 본문에 남은 `unknown`은 “RAG 연동 관련 근거보기 unknown 현상 수정”이라는 원문/요약 텍스트이며, 메타데이터 fallback 문제가 아니다.

## 2026-05-15 Slack 210개 이벤트 대비 ReviewItem 8개 및 표시 지연 확인

- 질문: Slack 이벤트가 210개인데 `review_items`가 8개인 것이 맞는지, 그리고 표시가 왜 오래 걸리는지 확인했다.
- 확인 결과:
  - 최신 Slack sync audit log 기준 `fetched_events=210`, `created_review_items=8`, `agent_generated_items=8`, `pending_review_count=8`이다.
  - 설계상 Slack 원본 이벤트와 ReviewItem은 1:1이 아니다. 원본 210개를 업무 신호 기준으로 필터링하고 LLM이 검토 가능한 지식 후보로 묶어 `decision_record`, `todo`, `history_event` 같은 후보 8개를 만든다.
  - 현재 DB에는 `review_items` 8개와 audit log는 남아 있지만 `sources`, `documents`, `document_versions`, `sync_jobs`는 0건이다. 이는 최근 수동 삭제/초기화로 원본 테이블이 비워지고 검토 후보/audit만 남은 상태로 보인다.
  - Slack API 수집 자체는 정상이며, 직접 connector fetch를 호출했을 때 이벤트 210개를 가져왔다.
- 표시 지연:
  - Review API 직접 호출은 약 128ms였다.
  - Playwright 기준 `/review` 첫 그룹 표시까지 약 221ms, 8개 그룹 전체 펼침 및 promotion-preview 호출까지 약 1초였다.
  - 따라서 검토사항 화면 렌더링 자체보다는 Slack sync 요청 안에서 수집 + LLM 분석 + ReviewItem 생성까지 모두 처리하는 구조가 오래 걸리는 원인이다.
- 다음 개선 방향:
  - Slack sync API는 원본 수집 job을 먼저 만들고 `job_id`를 즉시 반환한다.
  - Agent 분석/프로젝트 분류는 백그라운드 단계로 넘긴 뒤 프론트는 job 상태를 polling/SSE로 확인한다.
  - 이렇게 하면 긴 LLM 분석 중에도 프론트 프록시 `socket hang up` 없이 “원본 수집 중 → 검토 후보 생성 중 → 완료”를 안정적으로 표시할 수 있다.
## 2026-05-15 Slack 동기화 Internal Server Error 원인 확인

- 증상: 통합 화면에서 Slack 동기화 모달이 `원본 수집`, `AI 분석`까지 체크된 뒤 `검토 항목 저장` 단계에서 `Internal Server Error`를 표시했다.
- 서버 로그/DB 확인 결과:
  - Next 개발 서버 로그에 `/api/v1/integrations/slack/sync` 프록시 요청이 `socket hang up`으로 끊긴 기록이 있었다.
  - 백엔드 Python traceback은 확인되지 않았다.
  - 최신 `sync_jobs`는 `status=complete`, `progress_pct=100`이었다.
  - 최신 job id는 `slack-d92aabb68725410f941d263b45c06f0b`이고 메시지는 `fetched=205 created_review_items=11 skipped_events=0 pending_review_items=11`이었다.
  - 최신 audit log도 `integration.sync` 성공으로 기록되었다.
- 결론:
  - 실제 백엔드 Slack 수집, LLM 분석, ReviewItem 저장은 완료되었다.
  - 프론트엔드는 긴 단일 HTTP 요청이 완료 응답을 받기 전에 프록시/소켓이 끊겨 실패로 표시했다.
  - 따라서 이번 실패 표시는 데이터 저장 실패가 아니라 요청 수명/전송 계층 문제다.
- 후속 개선 방향:
  - Slack sync API가 긴 작업 전체를 한 요청에서 처리하지 않고 `job_id`를 즉시 반환하도록 바꾼다.
  - 원본 수집, AI 분석, 검토 항목 저장은 백그라운드 job 상태로 기록하고 프론트는 polling 또는 SSE로 진행률을 확인한다.
  - 이렇게 하면 1분 이상 걸리는 LLM 분석 중에도 브라우저 요청이 끊겨 `Internal Server Error`로 오인되는 문제를 줄일 수 있다.

## 2026-05-15 `project_assignment` 표시 혼동 수정

- 증상:
  - 검토사항 화면에서 `project_assignment` 타입이 영어 `project assignment`로 표시됐다.
  - 해당 항목의 Cost 타일이 `LLM 미사용`으로 보여, 새로 추가한 LLM 프로젝트 분류가 동작하지 않는 것처럼 보였다.
  - 상세 내용은 `source 연결`/짧은 summary 중심이라 어떤 프로젝트에 왜 연결되는지 한눈에 보기 어려웠다.
- 원인:
  - 새 LLM 프로젝트 라우팅은 Slack Agent가 만든 `todo`, `history_event`, `decision_record` 후보 payload에 `project_assignment_method: "llm_tool"` 형태로 붙는다.
  - 반면 `project_assignment` 타입은 여전히 `backend/app/projects/classifier.py`의 deterministic fallback/기존 항목이다.
  - Review UI가 이 두 경로를 구분해 설명하지 않고, `project_assignment` 타입 라벨도 한국어 매핑하지 않았다.
- 수정:
  - `frontend/src/app/review/page.tsx`의 타입 라벨에 `project_assignment: "프로젝트 연결"`을 추가했다.
  - `project_classifier` agent chip을 `프로젝트 분류기`로 표시한다.
  - deterministic 프로젝트 연결 항목은 Prompt `규칙 기반 프로젝트 연결`, Cost `추가 LLM 비용 없음`으로 표시한다.
  - `project_assignment` payload의 `project_name`, `task_summary`, `evidence_reason`, `source_title`, `source_type`을 별도 `프로젝트 연결 후보` 카드로 보여준다.
- TDD/검증:
  - RED: `frontend/e2e/review-agent-metadata.spec.ts`에서 `프로젝트 연결` 라벨과 상세 카드 기대값을 먼저 추가했고, 기존 UI에서 실패했다.
  - GREEN: `npm.cmd run test:visual -- review-agent-metadata.spec.ts` -> `2 passed`
  - 회귀: `npm.cmd run test:visual -- review-project-routing.spec.ts` -> `2 passed`
  - `npm.cmd exec tsc -- --noEmit`, `npm.cmd run lint`, `npm.cmd run build` 모두 통과했다.
- 주의:
  - 새 Slack LLM 경로는 `LLM 프로젝트 분류` 카드로 계속 표시된다.
  - 기존 DB에 남아 있는 `project_assignment` pending 항목은 규칙 기반 fallback 항목이므로 LLM 사용 항목으로 표시하지 않는다.

## 2026-05-15 Slack 프로젝트 Tool Routing 통합 작업계획서 작성

- 요청:
  - `project_assignment`도 규칙 기반이 아니라 할 일, 결정 기록, 히스토리처럼 LangChain tool 기반 LLM 판단으로 프로젝트에 묶이게 한다.
  - Slack 업무 후보가 등록 프로젝트에 해당하면 Review의 프로젝트 지정에 자동 선택되게 한다.
  - 등록 프로젝트에 해당하지 않으면 `프로젝트 선택` 상태로 두고, 사용자가 프로젝트를 선택하지 않으면 승인할 수 없게 한다.
  - 승인 후 타임라인은 프로젝트별/날짜별로 표시하고 프로젝트 탭에도 활동이 반영되게 한다.
  - 프로젝트 탭의 근거/활동/검토 metric 겹침도 Playwright로 확인한다.
- 계획서 위치:
  - `docs/superpowers/plans/2026-05-15-unified-slack-project-tool-routing.md`
- 계획 핵심:
  - 신규 Slack sync에서 규칙 기반 `project_assignment` 생성을 중단한다.
  - `backend/app/agents/slack_agent/sync_service.py`의 `topic_tag` 기반 fallback 프로젝트 지정도 제거한다.
  - Slack Agent 후보의 프로젝트 연결은 `agent_slack` LangGraph `project_route` node의 tool routing 결과만 사용한다.
  - 프로젝트 미선택 Slack Agent 후보는 promotion preview와 approve API에서 `project_key` 누락으로 승인 불가가 되게 한다.
  - Review UI는 `프로젝트 선택 후 승인 가능`과 `새 프로젝트 만들기` 링크를 보여준다.
  - Timeline UI는 날짜 단위 그룹을 추가한다.
  - Project UI는 metric 영역 모바일 겹침을 방지한다.
- 테스트 계획:
  - backend TDD: router unmatched 계약, sync service fallback 제거, Slack deterministic `project_assignment` 생성 중단, 승인 전 project_key 필수화, 프로젝트 메모리 연결 검증.
  - Playwright: Review 프로젝트 선택 필수, Timeline 날짜 그룹, Project metric 모바일 레이아웃, `/integrations -> /review -> /timeline -> /projects` 통합 흐름.

## 2026-05-15 Gmail/Google Drive 프로젝트 Tool Routing 분업 가이드 작성

- 요청:
  - Gmail과 Google Drive 데이터도 Slack Agent 방식처럼 LangChain tool 기반 LLM 프로젝트 판단으로 전환해야 한다.
  - Gmail/Drive 담당자가 Slack 담당자와 최대한 작업 영역을 겹치지 않고 분업할 수 있도록 가이드 문서를 작성한다.
- 문서 위치:
  - `docs/superpowers/runbooks/2026-05-15-gmail-drive-project-routing-collaboration-guide.md`
- 핵심 분업 원칙:
  - Gmail/Drive 담당자는 `backend/app/agents/mail_document_agent/`와 관련 테스트만 수정한다.
  - Slack 담당자는 `agent_slack/`, `backend/app/agents/slack_agent/`만 수정한다.
  - 프로젝트 Router 공용 계약은 `backend/app/agent_runtime/project_routing.py`로 분리한다.
  - Review 승인 정책, 통합 API, 프론트 UI, Playwright 통합 테스트는 별도 통합 담당자가 맡는다.
  - Mail/Document 담당자는 `agent_slack/project_routing.py`를 직접 import하지 않는다.
- Mail/Document 쪽 전환 방향:
  - 기존 `EvidencePacket -> MailDocumentAgent.run() -> ReviewCandidate -> ReviewItem` 흐름은 유지한다.
  - `MailDocumentAgent.run()` 이후 `project_route_mail_document_candidates()` 단계를 추가한다.
  - Gmail 본문+첨부 group, Drive 파일 단위 grouping은 유지한다.
  - ReviewItem payload에는 Slack과 동일한 `project_assignment_method`, `project_key`, `project_name`, `project_assignment_summary`, `project_assignment_reason`, `project_needs_user_selection` 필드를 저장한다.
- 테스트 방향:
  - backend는 fake router/fake connector로 Gmail group, Drive file, unmatched project, evidence/permission preservation을 검증한다.
  - Playwright는 통합 담당자가 Review/Timeline/Projects 화면 mock payload로 검증한다.

## 2026-05-15 Gmail/Google Drive B/C 개별 작업 문서 작성

- 요청:
  - 개발자 A는 Slack Agent를 계속 담당한다.
  - Gmail/Google Drive 고도화만 개발자 B와 C가 나누어 진행할 수 있도록 각각의 작업 문서를 작성한다.
  - 불필요한 역할을 추가하지 않고, 서로의 작업 영역을 최대한 건드리지 않는 방식으로 정리한다.
- 작성한 문서:
  - `docs/superpowers/runbooks/2026-05-15-developer-b-gmail-drive-agent-work.md`
  - `docs/superpowers/runbooks/2026-05-15-developer-c-gmail-drive-integration-work.md`
- 개발자 B 범위:
  - Gmail/Drive connector source 품질
  - Mail/Document Agent 추출 품질
  - Gmail 본문+첨부 grouping, Drive 파일 단위 grouping 유지
  - Mail/Document Agent ReviewItem payload에 LLM tool 프로젝트 라우팅 결과 저장
  - fake connector/fake model 기반 backend 테스트
- 개발자 C 범위:
  - 공용 프로젝트 라우팅 계약
  - Review 승인 정책과 프로젝트 선택 UX
  - 승인된 Gmail/Drive 항목의 Timeline/Projects 반영
  - 승인 기반 RAG indexing 연결
  - Playwright 기반 Review -> Timeline -> Projects 통합 확인
- 작업 경계:
  - B는 Slack Agent, Review UI, promotion, RAG, 프로젝트 서비스 영역을 직접 수정하지 않는다.
  - C는 Gmail/Drive connector와 Mail/Document Agent 내부 추출 로직을 직접 수정하지 않는다.

## 2026-05-15 Slack 프로젝트 Tool Routing 통합 완료

- 계획서:
  - `docs/superpowers/plans/2026-05-15-unified-slack-project-tool-routing.md`
- 구현:
  - 신규 Slack sync에서 규칙 기반 `project_assignment` 생성을 중단했다.
  - Slack Agent 저장 경로에서 `topic_tag` 기반 fallback 프로젝트 지정과 tag back-propagation을 제거했다.
  - Slack Agent 후보의 프로젝트 지정은 LangChain tool routing payload(`project_assignment_method=llm_tool`)만 신뢰한다.
  - 프로젝트 미선택 Slack Agent 후보는 promotion preview와 approve API에서 `project_key` 누락으로 승인할 수 없게 했다.
  - Review 화면에 `프로젝트 선택 후 승인 가능` 안내와 `새 프로젝트 만들기` 링크를 추가했다.
  - Timeline 화면은 승인된 프로젝트 타임라인 항목을 날짜 단위로 묶어 표시한다.
  - Projects 화면의 metric 영역은 모바일에서도 겹치지 않도록 1열/3열 반응형 grid와 `project-metric` test id를 적용했다.
- 테스트:
  - backend targeted: `65 passed`
  - ruff: `All checks passed!`
  - frontend TypeScript: passed
  - frontend lint: passed
  - frontend build: passed
  - Playwright:
    - `review-project-routing-required.spec.ts`
    - `timeline-project-date-groups.spec.ts`
    - `projects-responsive-metrics.spec.ts`
    - `slack-project-routing-flow.spec.ts`
    - desktop/mobile 총 `8 passed`

## 2026-05-15 동기화 진행률 재진입 UX 개선

- 요청:
  - Slack 동기화가 백그라운드에서 계속 실행될 때 사용자가 진행률을 알 수 없고, 닫은 진행 창을 다시 열 수 없는 문제를 수정한다.
- 구현:
  - `frontend/src/app/integrations/page.tsx`의 동기화 상태에 `progressPct`, `jobId`, `lastMessage`를 추가했다.
  - runtime status의 `latest_sync.progress_pct`와 `message`를 동기화 모달에 표시하도록 연결했다.
  - 동기화를 백그라운드로 보낸 뒤에도 작업 스트림 영역에 진행률 카드가 남고, `진행 창 열기`로 모달을 다시 열 수 있게 했다.
  - 페이지 로드 시 runtime status에 실행 중인 Slack sync가 있으면 진행률 카드를 바로 표시할 수 있도록 했다.
  - 백그라운드 실행 중에도 주기적으로 runtime status를 polling해서 완료/실패/진행률을 갱신한다.
- 테스트:
  - `npm run lint`: 통과
  - `npm run build`: 통과
  - `npm run test:visual -- integration-sync-modal.spec.ts --project=chromium-desktop`: `3 passed`
  - Playwright는 샌드박스에서 Chromium `spawn EPERM`으로 실패해 승인 후 재실행했다.

## 2026-05-15 타임라인/프로젝트 원본 링크 개선

- 요청:
  - 타임라인에서 `Open source`를 누르면 새 탭으로 열리게 한다.
  - 프로젝트 탭에서도 원본 근거를 볼 수 있는 링크를 제공한다.
- 구현:
  - `frontend/src/app/timeline/page.tsx`의 `Open source` 링크에 `target="_blank"`와 `rel="noopener noreferrer"`를 추가했다.
  - `frontend/src/app/projects/page.tsx`의 `연결된 원본 근거` 카드에 `source_url` 기반 `원본 근거` 링크를 추가했다.
  - `승인된 프로젝트 활동` 카드에도 첫 번째 `source_links`를 사용해 `원본 근거` 링크를 추가했다.
- 테스트:
  - `projects-source-links.spec.ts`를 추가해 프로젝트 근거/활동 링크의 href, 새 탭, rel 속성을 검증했다.
  - `timeline-project-date-groups.spec.ts`에 타임라인 `Open source` 새 탭 검증을 추가했다.
  - `npm run lint`: 통과
  - `npm run build`: 통과
  - `npm run test:visual -- projects-source-links.spec.ts timeline-project-date-groups.spec.ts --project=chromium-desktop`: `2 passed`

## 2026-05-15 타임라인 실제 source 시각 및 프로젝트 근거 개선

- 계획서:
  - `docs/superpowers/plans/2026-05-15-timeline-project-evidence-ux.md`
- 구현:
  - 프로젝트 API의 `ProjectTimelineItem`에 `occurred_at`을 추가했다.
  - Slack source URL 또는 `Source.raw_metadata.ts`에서 실제 Slack 대화 시각을 계산하고, 없으면 기존 승인/생성 시각으로 fallback한다.
  - 프로젝트 탭의 `연결된 원본 근거`는 legacy `project_assignment`뿐 아니라 승인된 프로젝트 활동의 source link/snippet에서도 생성하도록 바꿨다.
  - 타임라인 탭 리스트는 기본적으로 title만 보이게 정리했다.
  - 타임라인 날짜/시간은 `occurred_at` 기준으로 묶고 표시한다.
  - 타임라인은 기본적으로 최신 날짜 그룹만 보여주며, `날짜 전체 보기`와 날짜별 `자세히 보기/간단히 보기` 버튼으로 날짜 단위 compact/detail 전환이 가능하다.
  - Slack history 상세의 `Open source` 새 탭 동작을 popup까지 Playwright로 검증했다.
- 테스트:
  - backend: `uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q` → `44 passed`
  - ruff: `uv run ruff check backend/app/projects/service.py backend/tests/test_project_memory_api.py` → 통과
  - frontend: `npm run lint` → 통과
  - frontend: `npm run build` → 통과
  - Playwright: `npm run test:visual -- timeline-project-date-groups.spec.ts projects-source-links.spec.ts slack-project-routing-flow.spec.ts --project=chromium-desktop` → `3 passed`

## 2026-05-15 타임라인 날짜 Accordion UX 조정

- 요청:
  - 날짜를 기준으로 묶고, 날짜를 누르면 날짜만 보이거나 해당 날짜의 타임라인이 보이도록 한다.
  - 기존 `자세히 보기`에 있던 시간/source/status 정보를 title과 같은 카드 안에 함께 표시한다.
- 구현:
  - `날짜 전체 보기`, `자세히 보기`, `간단히 보기` 버튼을 제거하고 날짜 헤더 자체를 클릭 가능한 accordion 버튼으로 바꿨다.
  - 모든 날짜 헤더는 항상 표시한다.
  - 기본으로 최신 날짜가 펼쳐지고, 펼쳐진 날짜를 다시 누르면 날짜 헤더만 남도록 접힌다.
  - 닫힌 날짜를 누르면 해당 날짜의 타임라인 카드만 펼쳐진다.
  - 펼쳐진 타임라인 카드에는 title, 실제 source 시간, source type, 승인 상태, summary가 함께 표시된다.
- 테스트:
  - `npm run lint`: 통과
  - `npm run build`: 통과
  - `npm run test:visual -- timeline-project-date-groups.spec.ts slack-project-routing-flow.spec.ts --project=chromium-desktop`: `2 passed`

## 2026-05-15 타임라인 목록 summary 노출 제거

- 요청:
  - Slack history를 누르기 전 화면에 `result_summary`가 보이므로, 해당 내용은 Slack history 상세에서만 보이게 한다.
- 구현:
  - 펼쳐진 날짜의 타임라인 카드에서 summary 문단을 제거했다.
  - 타임라인 카드에는 title, 실제 source 시간, source type, 승인 상태, history 버튼만 남긴다.
  - Slack history 버튼을 누르면 오른쪽 상세 패널에서 기존 summary/history 내용을 볼 수 있다.
- 테스트:
  - `npm run lint`: 통과
  - `npm run build`: 통과
  - `npm run test:visual -- timeline-project-date-groups.spec.ts slack-project-routing-flow.spec.ts --project=chromium-desktop`: `2 passed`
