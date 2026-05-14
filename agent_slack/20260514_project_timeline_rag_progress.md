# Project Timeline and RAG Visibility Progress

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
