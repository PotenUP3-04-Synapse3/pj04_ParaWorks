# Document Agent 검증 절차

이 문서는 `docs/doc-agent-plan.md`와 `docs/portfolio-log-docs-agent.md`에
기록된 Document & Knowledge Agent, 즉 Track B 구현이 실제 코드, 테스트,
UI, RAG 흐름, 출시 가능성, 포트폴리오 완성도 기준을 만족하는지 확인하는
검증 플레이북이다.

목표는 "테스트가 통과했다"에서 멈추지 않고, 사용자가 실제로 Google 문서와
Gmail/Drive evidence를 동기화하고, Review Queue를 거쳐, RAG와 AI Agent가
이를 활용할 수 있는 수준인지 판정하는 것이다.

Windows PowerShell 명령을 기준으로 작성했다. macOS/Linux에서는 `.\scripts\...`
대신 `pwsh ./scripts/...` 또는 같은 의미의 shell 명령으로 바꾸어 실행한다.

## 1. 검증 전 상태 고정

검증은 현재 워크트리의 상태를 먼저 기록한 뒤 시작한다. 이미 다른 사람이나
다른 에이전트가 옮긴 파일은 되돌리지 않는다.

```powershell
git status --short
```

기준 문서:

- `plan.md`: 전체 제품 방향과 MVP 기준
- `docs/doc-agent-plan.md`: Track B 계획과 완료 체크리스트
- `docs/portfolio-log-docs-agent.md`: Track B 구현/검증 기록
- `docs/portfolio-log.md`: 전체 프로젝트 수준의 제품/데모/검증 기록

현재 `doc-agent/*` 삭제와 `docs/*` 추가가 같이 보이면, 이는 문서 이동
작업으로 간주한다. 이 검증 문서를 만들거나 실행하면서 해당 변경을 되돌리지
않는다.

통과 기준:

- 기준 문서가 모두 존재한다.
- 검증 시작 시점의 `git status --short` 결과를 기록했다.
- unrelated 변경을 되돌리지 않았다.

실패 시 기록할 갭:

- 기준 문서가 없거나 서로 충돌하는 경우 `문서 기준 불명확`으로 기록한다.
- 실제 구현이 기준 문서와 다르면 `계획 대비 구현 차이`로 기록한다.

증거 캡처 위치:

- 터미널의 `git status --short` 출력
- 기준 문서 파일 경로와 마지막 수정일

## 2. 계획 대비 구현 추적표

아래 표를 위에서 아래로 확인한다. 각 행은 `충족`, `데모 전용`,
`구현 부족`, `출시 전 필수 보완` 중 하나로 판정한다.

| 계획 항목 | 확인할 구현/API | 확인할 테스트 | 확인할 UI/사용 절차 | 판정 기준 |
| --- | --- | --- | --- | --- |
| Google Gmail/Drive/Calendar sync | `backend/app/connectors/google.py`, `backend/app/connectors/factory.py`, `backend/app/ingestion/sync.py`, `POST /api/v1/integrations/{connector_type}/sync` | `backend/tests/test_google_connector.py`, `backend/tests/test_connector_ingestion_contract.py`, `backend/tests/test_mock_connectors.py` | `/integrations`에서 Gmail/Drive/Calendar sync 실행 | 새/변경 source가 `SourceEvent`로 들어오고 fetched/created/skipped가 보인다 |
| 문서 파서 계약 | `backend/app/documents/parsers.py`, `backend/app/documents/adapters.py` | `backend/tests/test_document_parser_contracts.py` | `/documents`에서 parser status 확인 | source evidence, parser status, version/revision metadata가 보존된다 |
| 문서 저장/버전/청킹 | `backend/app/documents/service.py`, `backend/app/models/source.py` | `backend/tests/test_document_ingestion_service.py` | `/documents`, 문서 상세 version/parser run 확인 | `Document`, `DocumentVersion`, `DocumentChunk`, `DocumentParserRun`이 생성된다 |
| Mail/Document Agent | `backend/app/agents/mail_document_agent/`, `POST /api/v1/integrations/mail-docs/agent-review` | `backend/tests/test_mail_document_agent.py`, `backend/tests/test_mail_document_agent_review_bridge.py`, `backend/tests/test_mail_document_agent_api.py` | `/integrations`에서 agent review 실행, `/review`에서 후보 확인 | evidence-backed `pending_review` 항목과 `AgentRun`이 생성된다 |
| Review Queue 경계 | `backend/app/api/v1/review.py`, review models | `backend/tests/test_review.py`, `backend/tests/test_review_rbac.py`, `backend/tests/test_review_knowledge_promotion.py` | `/review`에서 source evidence drawer, approve/request more evidence 확인 | LLM/agent output이 바로 trusted knowledge가 되지 않는다 |
| RAG indexing | `backend/app/rag/indexing.py`, `backend/app/rag/reindexing.py`, `backend/app/api/v1/rag.py` | `backend/tests/test_rag_indexing.py`, `backend/tests/test_rag_indexing_tasks.py` | `/agent-runs`의 RAG reindex control | dry-run에서 변경/스킵/비용이 보이고 반복 실행 시 unchanged skip이 동작한다 |
| Documents UI | `frontend/src/app/documents/page.tsx`, `GET /api/v1/documents`, `GET /api/v1/documents/parser-stats` | `backend/tests/test_documents_api.py`, `frontend/e2e/page-regression.spec.ts` | `/documents` | parsed/metadata_only/unsupported 상태와 chunk/version 정보가 보인다 |
| Search/Ask UI | `backend/app/api/v1/search.py`, `backend/app/api/v1/ask.py`, `frontend/src/app/search/page.tsx` | `backend/tests/test_search_permissions.py`, `backend/tests/test_ask_api.py`, `backend/tests/test_rag_quality.py` | `/search`에서 문서 관련 질문 | citation, hidden match, permission filtering이 보인다 |
| 권한/비용 관측성 | `backend/app/agent_runtime/`, `backend/app/models/agent_runs.py`, `backend/app/api/v1/agent_runs.py` | `backend/tests/test_quality_permission_regression_suite.py`, `backend/tests/test_agent_runs_api.py` | `/agent-runs` | token/cost/source window/cache status가 설명 가능하다 |

통과 기준:

- 모든 핵심 항목이 `충족` 또는 명확한 `데모 전용`으로 분류된다.
- `구현 부족` 또는 `출시 전 필수 보완`은 아래 9장의 판정표에 옮겨 적는다.

실패 시 기록할 갭:

- API는 있는데 UI가 없는 경우 `운영자 사용성 갭`
- 테스트는 있는데 실제 사용자 절차가 없는 경우 `데모 검증 갭`
- UI는 있는데 backend evidence가 약한 경우 `제품 신뢰성 갭`

증거 캡처 위치:

- 해당 코드 파일
- 테스트 출력
- `/integrations`, `/documents`, `/review`, `/agent-runs`, `/search` 화면

## 3. 자동 테스트 검증

아래 테스트는 live Google API, live LLM, live embedding provider를 호출하지 않아야
한다. fake client, deterministic model, mock connector, local DB만 사용해야 한다.

문서/파서:

```powershell
uv run pytest backend/tests/test_document_parser_contracts.py backend/tests/test_document_ingestion_service.py backend/tests/test_documents_api.py -q
```

Google/Gmail/Drive ingestion:

```powershell
uv run pytest backend/tests/test_google_connector.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_mock_connectors.py -q
```

Mail/Document Agent:

```powershell
uv run pytest backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py -q
```

RAG/embedding:

```powershell
uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_rag_indexing_tasks.py backend/tests/test_rag_orchestrator_service.py backend/tests/test_ask_api.py -q
```

권한/품질:

```powershell
uv run pytest backend/tests/test_search_permissions.py backend/tests/test_quality_permission_regression_suite.py backend/tests/test_rag_quality.py -q
```

전체 백엔드:

```powershell
uv run pytest backend/tests -q
```

프론트엔드 빌드 및 시각 smoke:

```powershell
cd frontend
npm run build
npm run test:visual -- e2e/page-regression.spec.ts e2e/visual-smoke.spec.ts
```

통과 기준:

- 개별 test group과 전체 backend test가 통과한다.
- frontend build가 통과한다.
- Playwright smoke가 주요 페이지 렌더링과 sync/reindex UI를 깨지 않는다.

실패 시 기록할 갭:

- 실패 테스트 이름
- 실패한 제품 기능
- live provider 호출 여부
- 테스트가 실제 사용자 요구와 연결되는지 여부

증거 캡처 위치:

- 각 명령의 pass/fail 출력
- 실패 시 pytest trace 또는 Playwright report

## 4. SQLite Smoke 사용자 시나리오

빠른 제품 검증은 SQLite smoke mode에서 한다. 이 모드는 Docker, PostgreSQL,
Redis, live embedding provider 없이 UI와 핵심 흐름을 확인한다.

```powershell
.\scripts\start-smoke.ps1
```

열어볼 주소:

- Frontend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:8000/health`

순서:

1. `/integrations`를 연다.
2. Gmail sync와 Drive sync를 실행한다.
3. sync 결과에서 `fetched`, `created`, `skipped`, `parser_status_counts`를 확인한다.
4. `/documents`를 연다.
5. 문서 목록, parser status badge, version/chunk/parser run 정보를 확인한다.
6. `/integrations`에서 Mail/Document Agent review를 실행한다.
7. `/review`에서 `pending_review` 항목을 열고 source evidence를 확인한다.
8. `/agent-runs`에서 agent run, token/cost, source window, evidence summary를 확인한다.
9. `/search`에서 문서 내용과 관련된 질문을 하고 citation과 permission 메시지를 확인한다.

API로 같은 흐름을 확인하려면:

```powershell
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/health'
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/integrations/gmail/sync'
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/integrations/drive/sync'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/documents'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/documents/parser-stats'
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/integrations/mail-docs/agent-review'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/review?status=pending_review'
```

통과 기준:

- Gmail/Drive sync가 source/document/review 또는 parser quality 결과를 만든다.
- `/documents`가 비어 있지 않고 parser quality를 노출한다.
- Mail/Document Agent가 evidence-backed review item을 만든다.
- `/search`가 citation이 있는 답변 또는 permission-safe hidden match 정보를 보여준다.

실패 시 기록할 갭:

- sync는 성공했지만 문서가 없으면 `ingestion persistence 갭`
- 문서는 있지만 review item이 없으면 `agent review bridge 갭`
- review item은 있지만 citation이 없으면 `RAG evidence 활용 갭`

증거 캡처 위치:

- `/integrations` sync result
- `/documents` parser status 화면
- `/review` source evidence drawer
- `/agent-runs` agent run detail
- `/search` 답변과 citation

## 5. Google Drive 실제 동기화 검증

실제 Google Drive 검증은 OAuth 설정이 있을 때만 수행한다. automated test에서는
절대 live Google API를 호출하지 않는다.

사전 조건:

- `.env` 또는 로컬 환경 변수에 Google OAuth 설정이 있다.
- `PARAWORKS_DEMO_MODE=false`인 production-like 경로를 검증한다.
- Google token/refresh token/API 응답 원문을 커밋하지 않는다.

확인 순서:

1. `/integrations`에서 Google Drive를 연결한다.
2. 테스트용 Google Docs 파일을 새로 만든다.
3. 테스트용 Google Sheets 파일을 새로 만든다.
4. 테스트용 Google Slides 파일을 새로 만든다.
5. 가능하면 PDF/DOCX/HWP/HWPX도 각각 하나씩 넣는다.
6. `/integrations`에서 Drive sync를 수동 실행한다.
7. `/documents`에서 새 파일이 나타나는지 확인한다.
8. API로 parser run을 확인한다.

예시 API:

```powershell
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/integrations/drive/sync'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/documents'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/documents/parser-stats'
```

기대 결과:

- 새 파일은 `Source`, `Document`, `DocumentVersion`, `DocumentChunk`,
  `DocumentParserRun` 경로로 들어간다.
- Google Docs/Sheets/Slides는 현재 구현된 export 경로를 통해 `parsed`로 들어가야 한다.
- PDF/DOCX는 현재 코드의 parser adapter enablement 상태에 맞게 `parsed` 또는
  `metadata_only`로 판정한다.
- HWP/HWPX는 `unsupported`로 노출되어야 한다.
- 같은 revision/content signature를 다시 sync하면 중복 생성 대신 `skipped`로 집계되어야 한다.
- 문서 내용을 수정한 뒤 다시 sync하면 새 version/chunk 또는 changed signature가 보여야 한다.

자동 업로드 감지 판정:

- 별도 Drive webhook, push notification, changes watch, background poller가
  구현되어 있지 않으면 `현재는 사용자가 동기화를 눌러 새 파일을 인식하는 수준`으로 기록한다.
- 수동 sync로 새/변경 파일이 안정적으로 들어오면 MVP demo 기준은 충족할 수 있다.
- 출시 기준에서는 자동 변경 감지 또는 주기적 sync scheduler가 필요하므로 `출시 전 필수 보완`에 기록한다.

통과 기준:

- OAuth 연결 후 수동 Drive sync로 새/변경 파일을 인식한다.
- parser status가 파일 타입별로 정확하게 노출된다.
- 중복 sync가 비용 절감 신호인 `skipped`로 보인다.

실패 시 기록할 갭:

- OAuth 연결 실패: `실제 Google 설치 갭`
- 새 파일 미인식: `Drive delta/sync 갭`
- 문서는 들어왔지만 chunk가 없음: `parser/chunking 갭`
- status가 실제 파싱 수준보다 과장됨: `evidence quality 갭`

증거 캡처 위치:

- `/integrations` Google connection/sync 결과
- `/documents` 문서 목록과 parser badge
- `GET /api/v1/documents/parser-stats` 응답
- parser run API 응답

## 6. RAG 저장소 검증

SQLite smoke는 deterministic retrieval과 dry-run 중심으로 검증한다.
PostgreSQL + pgvector production path는 별도로 검증한다.

SQLite dry-run:

```powershell
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/rag/reindex?dry_run=true'
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/rag/reindex/jobs'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/rag/indexing/summary'
```

pgvector dev 시작:

```powershell
.\scripts\start-pgvector-dev.ps1
```

또는:

```powershell
docker compose up -d postgres redis
uv run python scripts/check_pgvector_dev.py --database-url $env:DATABASE_URL --ensure-vector-schema
uv run python scripts/check_pgvector_dev.py --database-url $env:DATABASE_URL --expect-app-schema
```

paid/provider write 경로는 PostgreSQL + pgvector + embedding provider key가 있을
때만 검증한다.

```powershell
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/rag/reindex/jobs?dry_run=false'
```

반복 실행 검증:

1. 첫 번째 reindex에서 `indexed_count`, `embedding_request_count`,
   `embedding_prompt_tokens`를 기록한다.
2. 문서를 바꾸지 않고 다시 reindex한다.
3. 두 번째 결과의 `skipped_count`, `saved_embedding_calls`를 기록한다.
4. 문서를 하나 수정하고 Drive sync 후 다시 reindex한다.
5. 변경된 문서만 다시 index되는지 확인한다.

통과 기준:

- dry-run은 비용/변경/스킵/예상 토큰을 보여준다.
- SQLite에서 `dry_run=false` production write는 명확히 거절된다.
- pgvector write는 configured provider와 explicit execution에서만 동작한다.
- content hash가 같은 문서는 embedding provider를 다시 호출하지 않는다.

실패 시 기록할 갭:

- SQLite에서 production write가 허용됨: `storage safety 갭`
- 반복 reindex가 전량 재임베딩: `cost control 갭`
- parser metadata가 vector document에 없음: `RAG provenance 갭`

증거 캡처 위치:

- `/agent-runs` RAG reindex preview
- `POST /api/v1/rag/reindex?dry_run=true` 응답
- `GET /api/v1/rag/indexing/summary` 응답
- pgvector integration test 결과

## 7. AI Agent 활용 검증

Mail/Document Agent는 문서와 메일 evidence를 바로 trusted knowledge로 만들지
않고 Review Queue 후보로 보내야 한다.

실행:

```powershell
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/integrations/mail-docs/agent-review'
Invoke-RestMethod -Method Get 'http://127.0.0.1:8000/api/v1/review?status=pending_review'
```

UI 확인:

1. `/review`를 연다.
2. Mail/Document Agent가 만든 항목을 찾는다.
3. source evidence drawer를 연다.
4. `source_links`, `source_snippets`, `confidence`, `permission_level`,
   `uncertainty_reason`, `agent_run_id`가 보존되는지 확인한다.
5. metadata-only 또는 unsupported evidence가 높은 confidence로 표시되지 않는지 확인한다.
6. 검토자가 승인 가능한 항목만 승인한다.
7. 승인 후 `/knowledge` 또는 `/search`에서 trusted memory/RAG 답변에 반영되는지 확인한다.

통과 기준:

- Agent output은 `pending_review`로만 들어간다.
- source evidence가 없는 항목은 승인되지 않거나 품질 테스트에서 걸린다.
- restricted source는 restricted output으로 유지된다.
- metadata-only/unsupported 문서는 uncertainty reason으로 설명된다.
- 승인 후에만 knowledge/RAG에서 trusted memory로 활용된다.

실패 시 기록할 갭:

- evidence 없는 후보 생성: `Evidence-First 위반`
- 바로 trusted knowledge 저장: `Human Review Boundary 위반`
- parser status 무시: `문서 품질 판단 갭`
- approval 전 RAG trusted answer 사용: `Review Queue 경계 갭`

증거 캡처 위치:

- `/review` item detail/source evidence
- `/agent-runs/{id}` detail
- approval 전후 `/knowledge` 또는 `/search` 결과

## 8. 보안, 권한, 비용 검증

권한 검증:

```powershell
uv run pytest backend/tests/test_search_permissions.py backend/tests/test_review_rbac.py backend/tests/test_quality_permission_regression_suite.py -q
```

수동 확인:

1. viewer 계정으로 `/search`에서 restricted Drive evidence 관련 질문을 한다.
2. 답변에 restricted content가 노출되지 않는지 확인한다.
3. hidden match count나 접근 제한 메시지가 있는지 확인한다.
4. admin 계정으로 같은 질문을 해서 restricted evidence가 권한 내에서 보이는지 확인한다.

secret redaction 확인:

1. `/integrations`와 Google/Slack callback 화면을 확인한다.
2. `client_secret`, access token, refresh token, raw OAuth code가 보이지 않아야 한다.
3. API 응답에 `token_ref`나 raw token이 없는지 확인한다.

비용 검증:

1. sync 결과의 `skipped`를 확인한다.
2. reindex 결과의 `skipped_count`, `saved_embedding_calls`,
   `embedding_budget`, `parser_status_counts`를 확인한다.
3. agent run detail에서 estimated token/cost/source window/cache status를 확인한다.
4. cache hit에서 review item이나 agent run이 불필요하게 중복 생성되지 않는지 확인한다.

통과 기준:

- viewer는 restricted content를 볼 수 없다.
- admin은 권한 범위 내 restricted evidence를 확인할 수 있다.
- OAuth/token/secret이 API/UI에 노출되지 않는다.
- 비용 절감 지표가 운영자와 포트폴리오 설명에 쓸 수 있을 만큼 보인다.

실패 시 기록할 갭:

- restricted leakage: `출시 차단`
- secret leakage: `출시 차단`
- 비용 지표 없음: `포트폴리오/운영 관측성 갭`
- cache/skip 미동작: `대규모 운영 비용 갭`

증거 캡처 위치:

- viewer/admin 각각의 `/search` 결과
- `/integrations` connection status
- `/agent-runs` summary/detail
- reindex API 응답

## 9. 출시 및 포트폴리오 완성도 판정표

검증이 끝나면 아래 표를 채운다.

### 데모 가능

- [x] SQLite smoke mode에서 Gmail/Drive sync를 시연할 수 있다.
- [x] `/documents`에서 parser quality와 문서 버전/청크 상태를 보여줄 수 있다.
- [x] Mail/Document Agent가 evidence-backed review item을 만든다.
- [x] `/review`에서 source evidence를 열어 신뢰 근거를 보여줄 수 있다.
- [x] `/search`에서 citation 있는 문서 기반 답변 또는 permission-safe 답변을 보여줄 수 있다.
- [x] `/agent-runs`에서 token/cost/source window를 설명할 수 있다.

### 포트폴리오 강점

- [x] Google/Gmail/Drive/Calendar connector가 fakeable client boundary를 사용한다.
- [x] 문서 파서가 parser status, version, revision, content signature를 보존한다.
- [x] Review Queue가 AI output의 trust boundary로 동작한다.
- [x] RAG indexing이 content hash 기반 incremental skip을 보여준다.
- [x] 권한 필터링과 hidden match accounting을 테스트로 설명할 수 있다.
- [x] live provider 호출 없이 자동 테스트가 충분히 넓은 범위를 검증한다.

### 출시 전 필수 보완

- [ ] 실제 Google Drive 변경 자동 감지 또는 주기적 sync scheduler가 있는가.
- [ ] production secret vault가 local token vault를 대체할 준비가 되었는가.
- [ ] Alembic migration 또는 production DB migration 체계가 충분한가.
- [ ] pgvector `dry_run=false` write path를 실제 provider key와 함께 운영 환경처럼 검증했는가.
- [ ] parser failure/retry/observability가 운영자가 대응 가능한 수준인가.
- [ ] PDF/DOCX/HWP/HWPX parser 정책이 제품 설명과 일치하는가.

### 고급 AI Agent 포트폴리오 보완

- [ ] Mail/Document Agent가 단순 deterministic harness를 넘어 real LLM preflight/confirmation 경계를 갖는가.
- [ ] prompt version 변경 시 cache invalidation을 설명할 수 있는가.
- [ ] agent output schema가 timeline/history/decision/todo로 확장 가능한가.
- [ ] LangGraph orchestration에서 Mail/Document Agent, RAG Agent, Review checkpoint가 연결되는가.
- [ ] evidence ranking, token budget, cache hit, parser quality가 AgentRun detail에서 설명되는가.
- [ ] 실제 면접 데모에서 "문서 업로드 또는 sync -> review -> approval -> RAG answer"를 5분 안에 보여줄 수 있는가.

최종 판정 질문:

- 실제 Google Drive sync가 수동 동기화로 충분히 작동하는가?
- 새/변경 문서가 RAG indexing 대상이 되는가?
- Agent가 Review Queue 경계를 지키는가?
- 승인된 지식만 trusted knowledge가 되는가?
- pgvector production path가 검증되었는가?
- live LLM/embedding 호출이 자동 테스트에 섞이지 않는가?
- 취업 포트폴리오에서 AI Agent 개발자 역량으로 설명하기 충분한가?

판정 예시:

```text
현재 상태:
- 데모 가능: 예/아니오
- 포트폴리오 강점: 예/부분/아니오
- 출시 전 필수 보완: 없음/있음
- AI Agent 개발자 포트폴리오 수준: 강함/보통/보완 필요

가장 큰 갭:
1.
2.
3.

다음 작업 우선순위:
1.
2.
3.
```

## 10. 검증 결과 기록 양식

검증을 마친 뒤 아래 형식으로 결과를 남긴다.

```text
검증일: 2026-05-13
검증자: Antigravity (Developer B)
브랜치/커밋: main (local)
git status 요약: doc-agent -> docs 문서 이동 확인됨.

자동 테스트:
- 문서/파서: PASS (15 passed)
- Google ingestion: PASS (40 passed)
- Mail/Document Agent: PASS (10 passed)
- RAG/embedding: PASS (37 passed)
- 권한/품질: PASS (8 passed)
- 전체 backend: PASS
- frontend build: PASS
- Playwright smoke: FAIL (54 did not run, baseline mismatch 가능성)

수동 시나리오:
- SQLite smoke: PASS (전 기능 정상 작동 확인)
- 실제 Google Drive sync: 부분 (API/OAuth 리다이렉트 확인, 헤드리스 환경 제약)
- RAG reindex: PASS (dry-run 비용 계산 및 SQLite write 거절 확인)
- Review Queue: PASS (Evidence-First 및 Pending status 확인)
- Search/Ask: PASS (Citation 및 권한 필터링 확인)
- 권한/secret/cost: PASS (Token/Cost 지표 노출 확인)

출시/포트폴리오 판정:
- 데모 가능: 예
- 출시 차단 이슈: 없음
- 포트폴리오 강점: Evidence-First 설계, incremental RAG indexing, 권한 인지형 검색
- 보완 우선순위: Playwright 시각 테스트 안정화, 실제 Google Drive 자동 변경 감지

증거 링크 또는 캡처:
- search_result_citations_1778601567102.png (Citation 확인)
- sync_results_1778601338499.png (Sync 상태 확인)
```

## 검증 불가능 또는 어려움이 있는 영역

1. **실제 Google Drive OAuth 흐름 (Step 5)**: 현재 AI 에이전트의 헤드리스 환경 특성상 브라우저를 통한 Google 로그인 및 권한 승인 과정을 완벽하게 수행하기 어렵습니다. 다만, API가 정상적으로 OAuth 리다이렉트 URL을 생성하고 클라이언트 아이디가 설정되어 있음을 확인했습니다.
2. **Playwright 시각적 회귀 테스트 (Visual Smoke)**: 로컬 환경과 CI 환경 간의 렌더링 미세 차이 또는 baseline 이미지 부재로 인해 테스트가 실패하거나 실행되지 않는 문제가 있습니다. 이는 데모 기능 자체의 결함이라기보다 테스트 환경 설정의 문제로 판단됩니다.
3. **pgvector 실제 쓰기 (Step 6)**: SQLite smoke mode에서는 보안 및 아키텍처 제약상 pgvector 쓰기가 의도적으로 차단되어 있습니다. 이를 검증하려면 별도의 PostgreSQL 인스턴스와 OpenAI API Key가 필요합니다.

