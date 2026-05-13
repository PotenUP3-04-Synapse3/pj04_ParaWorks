# 연동관리/검토사항/타임라인 기능 점검

작성일: 2026-05-13  
대상: `/integrations`, `/review`, `/timeline`

## 요약

세 페이지 모두 UI는 존재하지만, 실제 서비스 흐름 기준으로는 아직 연결이 덜 된 부분이 있습니다.

- `/timeline`은 현재 실제 백엔드 데이터를 전혀 읽지 않습니다.
- `/review`는 검토/승인 화면은 있지만 권한 필터, 타입 계약, 타임라인 승격이 불완전합니다.
- `/integrations`는 기능이 가장 많이 연결되어 있으나, 일부 상태 갱신과 오류 처리, 공통 모듈화가 부족합니다.
- 세 페이지의 Playwright 최소 렌더링 테스트는 현재 인증 401로 로그인 화면에 떨어져 실패했습니다. 이는 페이지 자체 기능 이전에 인증 세션 준비/테스트 셋업 문제가 있음을 뜻합니다.

검증 명령:

```powershell
npm.cmd run test:visual -- page-regression.spec.ts --project=chromium-desktop -g "(review|timeline|integrations) renders cleanly in light mode"
```

결과:

- `review renders cleanly in light mode` 실패
- `timeline renders cleanly in light mode` 실패
- `integrations renders cleanly in light mode` 실패
- 공통 실패 원인: `Failed to load resource: the server responded with a status of 401 (Unauthorized)`
- 스냅샷상 세 페이지 모두 의도한 페이지 대신 `/login` 화면이 렌더링됨

## 공통 문제

### 1. 인증 실패 시 세 페이지가 실제 화면까지 도달하지 못함

위치:

- `frontend/src/components/layout/AppShell.tsx:99`
- `frontend/src/components/layout/AppShell.tsx:107`
- `frontend/src/components/layout/AppShell.tsx:108`

현재 AppShell은 `/api/v1/auth/me`가 실패하면 즉시 `/login`으로 이동합니다. 프로덕션 서비스 관점에서는 맞는 동작이지만, 현재 회귀 테스트와 로컬 확인 흐름에서는 인증 세션이 없으면 `/integrations`, `/review`, `/timeline` 자체를 검증하지 못합니다.

영향:

- 세 페이지의 실제 기능 문제를 Playwright 기본 회귀 테스트가 가려버립니다.
- 인증 없는 상태에서 “페이지가 안 뜬다”는 증상이 모두 로그인 화면으로 수렴합니다.
- 페이지별 API/렌더링 오류와 인증 오류를 분리해 보기 어렵습니다.

권장:

- 페이지 회귀 테스트에는 로그인 세션 또는 `/api/v1/auth/me` mock을 공통 fixture로 추가합니다.
- 실제 앱에서는 로그인 redirect를 유지하되, 테스트는 authenticated shell 상태에서 페이지별 기능을 검증합니다.

## `/timeline` 점검

### 1. 실제 데이터 연결이 없음

위치:

- `frontend/src/app/timeline/page.tsx:24`
- `frontend/src/app/timeline/page.tsx:127`
- `frontend/src/app/timeline/page.tsx:143`
- `backend/app/api/v1/knowledge.py:270`

`projectTimelineSeedData`에는 하드코딩된 프로젝트/히스토리 데이터가 남아 있지만, 실제 렌더링에는 사용되지 않습니다. 렌더링에 쓰이는 `projectTimelines`는 빈 배열입니다.

현재 결과:

- Slack/Gmail/Drive/Calendar 연동이나 Review 승인이 있어도 `/timeline`은 백엔드 API를 호출하지 않습니다.
- 화면은 항상 “Slack 또는 Google을 연동하면...”과 `0개 히스토리` 상태로 떨어질 수 있습니다.
- 백엔드에는 `/api/v1/knowledge`의 `timeline_events` 응답이 있으나 페이지가 사용하지 않습니다.

권장:

- `/timeline`을 `GET /api/v1/knowledge` 또는 별도 `GET /api/v1/timeline`에 연결합니다.
- `KnowledgeItem` 기반의 `TimelineEventViewModel` 변환 함수를 별도 모듈로 둡니다.
- 빈 상태, 로딩 상태, API 실패 상태를 분리합니다.

### 2. 타임라인 후보가 승인되어도 TimelineEvent로 승격되지 않음

위치:

- `backend/app/knowledge/promotion.py:6`
- `backend/app/knowledge/promotion.py:31`
- `frontend/src/app/review/page.tsx:83`

프론트는 `timeline_event`를 검토 타입으로 표시하지만, 백엔드 promotion 대상에는 `decision_record`, `history_event`, `todo`만 포함됩니다. 따라서 `timeline_event` ReviewItem은 승인해도 `TimelineEvent` 테이블로 승격되지 않습니다.

영향:

- 사용자가 검토사항에서 타임라인 후보를 승인해도 `/timeline`에 표시될 실제 데이터가 생기지 않습니다.
- “검토사항 → 타임라인” 제품 흐름이 끊깁니다.

권장:

- `PROMOTABLE_REVIEW_TYPES`에 `timeline_event`를 추가합니다.
- `promote_review_item`에 `TimelineEvent` 생성 분기를 추가합니다.
- 필수 payload 필드(`title`, `result_summary` 등)를 명확히 테스트합니다.

### 3. 원문 링크가 앱/브라우저에서 열 수 없는 내부 스킴

위치:

- `frontend/src/app/timeline/page.tsx:37`
- `frontend/src/app/timeline/page.tsx:52`
- `frontend/src/app/timeline/page.tsx:66`
- `frontend/src/app/timeline/page.tsx:80`
- `frontend/src/app/timeline/page.tsx:265`

하드코딩 데이터의 `sourceUrl`은 `paraworks://...` 형식입니다. 실제 브라우저에서는 대부분 열 수 없고, 현재는 실제 source evidence drawer나 connector 원문 링크와 연결되지 않습니다.

권장:

- Slack/Gmail/Drive/Calendar별 원문 링크는 `source_links` 또는 `source_evidence`에서 가져옵니다.
- 앱 내부 라우팅이 필요하면 `/messages`, `/documents`, `/projects` 같은 실제 route로 변환합니다.

## `/review` 점검

### 1. ReviewResponse 타입이 프론트에서 중복 정의됨

위치:

- `frontend/src/app/review/page.tsx:39`
- `frontend/src/lib/api/types.ts:365`

전역 API 타입의 `ReviewResponse`는 `items`만 가지고 있는데, `/review/page.tsx`는 로컬 타입으로 `groups`와 `items`를 다시 정의합니다.

영향:

- API 계약이 한 곳에서 관리되지 않습니다.
- 백엔드 응답 shape이 바뀌어도 타입 단에서 일관되게 깨지지 않습니다.
- 다른 페이지나 테스트에서 `ReviewResponse`를 재사용하기 어렵습니다.

권장:

- `ReviewGroup`, `ReviewResponse`를 `frontend/src/lib/api/types.ts`로 이동합니다.
- `/review/page.tsx`는 공통 타입만 import하게 만듭니다.

### 2. 목록/수정/프리뷰 API가 권한 필터를 일관되게 적용하지 않음

위치:

- `backend/app/api/v1/review.py:46`
- `backend/app/api/v1/review.py:147`
- `backend/app/api/v1/review.py:168`
- `backend/app/api/v1/review.py:182`
- `backend/app/core/demo_filters.py:10`

`approve`에서는 `ensure_can_review_permission`을 호출하지만, 목록 조회, 수정, promotion-preview 조회에서는 현재 사용자 권한을 받거나 검사하지 않습니다. 또한 `filter_review_items`가 import되어 있지만 `list_review_items`에서는 사용되지 않습니다.

영향:

- 제한 권한 항목이 목록/프리뷰/수정 경로에서 노출될 수 있습니다.
- non-demo 모드에서 mock source를 숨기는 정책이 Review 목록에는 적용되지 않습니다.
- 승인 단계에서만 막히므로 사용자는 “보이는데 승인 안 됨” 같은 불일치를 경험할 수 있습니다.

권장:

- `list_review_items`, `update_review_item`, `preview_review_item_promotion`에도 `CurrentUser`, `AppSettings`를 주입합니다.
- 목록 단계에서 permission filtering과 demo/mock filtering을 적용합니다.
- 수정 권한도 승인 권한과 같은 정책으로 제한합니다.

### 3. Preview API 하나가 실패하면 전체 Review 화면 로드가 실패함

위치:

- `frontend/src/app/review/page.tsx:119`
- `frontend/src/app/review/page.tsx:122`

모든 review item의 promotion preview를 `Promise.all`로 한 번에 가져옵니다. 항목 하나의 preview API가 404/400/500이면 전체 `loadItems`가 catch로 떨어지고 화면 전체가 오류 상태가 됩니다.

권장:

- `Promise.allSettled`로 바꾸고 실패한 preview는 해당 item에만 “프리뷰 불가” 상태를 표시합니다.
- preview fetch를 펼친 그룹 또는 항목별 lazy load로 분리합니다.

### 4. 그룹 상태 업데이트가 서버 truth와 어긋날 수 있음

위치:

- `frontend/src/app/review/page.tsx:161`
- `frontend/src/app/review/page.tsx:165`

승인/반려/근거 요청 후 로컬에서 해당 item만 제거합니다. 그룹의 `total_count`, `avg_confidence`, `status`, `permission_level`은 재계산하지 않습니다.

영향:

- 같은 그룹에 여러 항목이 있을 때 헤더의 개수/평균 신뢰도가 실제와 달라질 수 있습니다.
- 서버의 새 그룹 상태와 클라이언트 상태가 달라집니다.

권장:

- 액션 후 `loadItems()`를 다시 호출하거나, 그룹 재계산 helper를 별도 모듈로 둡니다.

## `/integrations` 점검

### 1. live manifest scope 계약이 mock manifest에서 파생되던 문제

위치:

- `backend/app/connectors/registry.py`
- `backend/app/connectors/mock.py:28`
- `backend/app/connectors/google.py:27`

점검 중 발견했고, `gmail.send` scope 추가 작업 범위에 포함해 수정했습니다. 이제 live 모드 manifest는 Google connector의 실제 scope 계약을 사용합니다.

검증:

```powershell
uv run pytest backend/tests/test_google_oauth.py backend/tests/test_google_connector.py backend/tests/test_connector_factory.py::test_sync_connector_uses_installed_google_connection_token_from_vault backend/tests/test_connector_ingestion_contract.py::test_connector_manifests_define_parallel_ingestion_contracts backend/tests/test_connector_ingestion_contract.py::test_live_gmail_manifest_reports_send_scope_for_approval_actions backend/tests/test_assistant_api.py::test_assistant_email_draft_requires_approval_endpoint_before_send -q
```

결과: `34 passed`

### 2. 동기화 후 Google runtime status를 갱신하지 않음

위치:

- `frontend/src/app/integrations/page.tsx:294`
- `frontend/src/app/integrations/page.tsx:301`
- `frontend/src/app/integrations/page.tsx:242`

`startSync` 후 Slack인 경우만 `/api/v1/integrations/slack/runtime-status`를 다시 조회합니다. Gmail/Drive/Calendar sync 후에는 `googleRuntimeByType`을 갱신하지 않습니다.

영향:

- 사용자가 Gmail/Drive/Calendar 동기화를 실행해도 오른쪽 Google 운영 상태가 오래된 값으로 남을 수 있습니다.
- 작업 결과 패널과 Google 운영 상태 패널이 서로 다른 상태를 보여줄 수 있습니다.

권장:

- connector type이 Google 계열이면 해당 `/{connector_type}/runtime-status`를 재조회합니다.
- `refreshRuntimeStatus(type)` 같은 공통 helper로 모듈화합니다.

### 3. connector 미연결 오류가 API에서 명확히 처리되지 않음

위치:

- `backend/app/api/v1/integrations.py:25`
- `backend/app/api/v1/integrations.py:197`
- `backend/app/connectors/factory.py:16`
- `backend/app/connectors/factory.py:35`

`ConnectorNotConfiguredError`는 import되어 있지만 `sync_connector`에서 catch하지 않습니다. non-demo/live 모드에서 OAuth 연결이 없으면 user-facing 409/400 대신 서버 예외로 보일 수 있습니다.

권장:

- `sync_connector`에서 `ConnectorNotConfiguredError`를 catch해 `409`와 명확한 detail을 반환합니다.
- 프론트는 이 detail을 “OAuth 연결 필요” 안내로 표시합니다.

### 4. Gmail/Drive가 같은 Mail/Docs Agent 실행 key를 공유함

위치:

- `frontend/src/app/integrations/page.tsx:56`
- `frontend/src/app/integrations/page.tsx:67`
- `frontend/src/app/integrations/page.tsx:334`
- `frontend/src/app/integrations/page.tsx:418`

Gmail과 Drive의 `agentAction.key`가 모두 `mail-docs`입니다. 하나를 실행하면 두 카드의 실행 상태가 동시에 바뀔 수 있습니다. 백엔드 endpoint도 같은 `/mail-docs/agent-review`라 의도일 수 있지만, UI상 “Gmail 카드에서 실행했는지 Drive 카드에서 실행했는지”가 구분되지 않습니다.

권장:

- 카드별 액션이 같은 파이프라인을 실행한다면 “Mail/Docs/Calendar 통합 Agent”를 별도 공통 섹션으로 분리합니다.
- 카드 내부 버튼은 “소스 동기화”만 담당하게 해 역할을 단순화합니다.

### 5. 소스 현황 fallback 수치가 하드코딩되어 있음

위치:

- `frontend/src/app/integrations/page.tsx:654`
- `frontend/src/app/integrations/page.tsx:655`
- `frontend/src/app/integrations/page.tsx:656`

`DashboardResponse`가 없으면 SourceOperationsPanel은 `slack: 128`, `gmail: 62` 같은 정적 숫자를 보여줍니다.

영향:

- 백엔드가 내려가거나 인증 실패가 있어도 실제처럼 보이는 숫자가 표시될 수 있습니다.
- 운영자가 “현재 수집량”으로 오해할 수 있습니다.

권장:

- fallback 숫자 대신 “데이터를 불러오지 못했습니다” 또는 skeleton/empty state를 표시합니다.
- 데모용 숫자가 필요하면 명시적으로 “demo sample” 라벨을 붙입니다.

### 6. IntegrationsPage가 너무 많은 책임을 가짐

위치:

- `frontend/src/app/integrations/page.tsx:108`
- `frontend/src/app/integrations/page.tsx:128`
- `frontend/src/app/integrations/page.tsx:294`
- `frontend/src/app/integrations/page.tsx:334`
- `frontend/src/app/integrations/page.tsx:363`

한 파일에서 manifest 로딩, OAuth URL 조회, runtime status 조회, sync 실행, Slack 채널 선택, LLM preflight/run, agent run, 작업 스트림 표시를 모두 처리합니다.

영향:

- 작은 기능 하나를 고쳐도 페이지 전체 상태를 건드리기 쉽습니다.
- Slack과 Google 흐름이 분리되지 않아 확장 시 회귀 가능성이 큽니다.

권장:

- `useIntegrationManifests`, `useConnectorRuntimeStatus`, `useConnectorSync`, `useOAuthInstallUrls` 같은 hook으로 분리합니다.
- `SlackRuntimeStatusPanel`, `GoogleRuntimeStatusList`, `ConnectorCard`, `SourceOperationsPanel`의 데이터 변환을 page 밖 순수 함수로 이동합니다.

## 우선순위 제안

1. 인증된 Playwright fixture를 추가해 세 페이지가 실제 화면으로 진입하도록 만들기
2. `/timeline`을 실제 `knowledge.timeline_events` 또는 신규 timeline API에 연결하기
3. `timeline_event` ReviewItem 승인 → `TimelineEvent` 승격 경로 추가하기
4. Review API 목록/프리뷰/수정에 권한 필터와 mock filtering 적용하기
5. `/integrations` sync 오류 처리와 Google runtime status refresh 보강하기
6. Integrations/Review 페이지의 타입과 상태 로직을 공통 타입 및 hook으로 모듈화하기
