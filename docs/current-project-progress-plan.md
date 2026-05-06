# ParaWorks Current Project Progress Plan

작성일: 2026-05-06

## 1. 검토한 문서와 결론

검토 문서:

- `AGENTS.md`
- `C:\Users\user\Documents\Obsidian Vault\Paraworks_Project_Plan_wbs.md`
- `C:\Users\user\Documents\Obsidian Vault\PROJECT_TASK_AUDIT.md`

보조 기준:

- `plan.md`
- `docs/portfolio-log.md`
- `docs/superpowers/runbooks/session-handoff.md`
- 최신 관련 spec/plan: Google Identity/RBAC 문서
- 현재 저장소 코드와 테스트 상태

결론: 세 문서는 모두 같은 ParaWorks 작업을 다룬다. 다만 문서의 성격과 시점이 다르므로 서로 동일한 계획서는 아니다.

- `Paraworks_Project_Plan_wbs.md`는 원 기획 발표/WBS 문서다. 문제 정의, MVP 범위, 예상 시나리오, 2주 개발 역할 분담을 설명한다.
- `PROJECT_TASK_AUDIT.md`는 2026-05-04 시점의 코드 감사 문서다. 당시 빌드 차단 요소와 추가 작업을 넓게 정리했지만, 현재 코드 기준으로는 일부 내용이 오래되었다.
- `AGENTS.md`는 현재 저장소의 협업/개발 규칙 문서다. 세 개발자가 Slack Agent, Mail/Document Agent, RAG/Orchestrator Agent를 나누어 소유한다는 실행 원칙을 정의한다.

현재 실행 기준은 저장소 루트의 `plan.md`다. 외부 WBS와 감사 문서는 방향성과 과거 상태를 확인하는 참고 자료로 사용하고, 충돌이 있으면 `plan.md`와 현재 코드 상태를 우선한다.

## 2. 전체 작업 Plan 재작성

### A. 제품 방향과 협업 계약

완료:

- ParaWorks의 제품 목표가 "한국어 우선, 근거 중심, 권한 인식형 회사 메모리 플랫폼"으로 정리되었다.
- 세 개발자 트랙이 Slack Agent, Mail/Document Agent, RAG/Orchestrator Agent로 재정의되었다.
- `AgentManifest`, `AgentRegistry`, `EvidencePacket`, `ReviewCandidate`, `AgentRunCost`, `PermissionContext` 등 공유 계약이 `backend/app/agent_runtime/`에 존재한다.
- Evidence-first, Review Queue trust boundary, 비용 정책, 권한 정책이 `AGENTS.md`와 `plan.md`에 문서화되었다.

작업중:

- shared contract를 유지하면서 각 agent 트랙이 더 실제 데이터 품질에 가까워지도록 정리 중이다.
- portfolio/demo 기준으로 제품 설명, runbook, case study를 계속 보강 중이다.

해야 할 것:

- output schema, permission policy, token budget policy 변경 시 의사결정 기록을 남긴다.
- 장기적으로 branch/integration pipeline을 실제 협업 방식과 맞춰 운영한다.

### B. Connector와 Ingestion

완료:

- Slack, Gmail, Google Drive, Calendar connector boundary가 존재한다.
- Slack OAuth, Google OAuth, installed sync boundary가 구현되어 있다.
- connector 공통 입력은 `SourceEvent`와 `ConnectorManifest`를 사용한다.
- Slack thread context, Gmail thread/domain metadata, Drive parser/version metadata, Calendar attendee/status metadata가 보강되었다.
- connector golden dataset fixture가 Slack/Gmail/Drive/Calendar metadata expectations를 고정한다.

작업중:

- Google Drive는 현재 metadata-only parser status와 version/revision 정보를 보존하는 단계다.
- 실제 파일 타입별 파싱 품질과 parser run 기록은 더 보강해야 한다.

해야 할 것:

- Drive 파일 타입별 parser adapter를 확정한다.
- HWP/HWPX parser adapter 방향을 결정한다.
- live connector 검증은 fake client 기반 자동 테스트와 분리하고, 실제 API 호출은 수동 smoke로 제한한다.
- connector별 sync 실패, pagination, rate limit, token refresh를 더 촘촘히 검증한다.

### C. Agent와 LangGraph Orchestration

완료:

- Slack Agent, Mail/Document Agent, RAG/Orchestrator Agent가 독립 slice로 구현되어 있다.
- LangGraph company-memory workflow foundation이 존재한다.
- Track C memory extraction boundary가 Timeline, History, Decision Record, Todo, Validation까지 확장되었다.
- LangChain structured-output adapter가 deterministic contract 뒤에 추가되었다.
- Slack live LLM path에는 OpenAI primary, Gemini fallback, paid-run preflight, evidence ranking, budget cap이 있다.

작업중:

- deterministic harness와 structured-output adapter 사이의 품질 검증을 넓히는 단계다.
- Slack/Google 실제 evidence quality를 agent 입력에 더 안정적으로 반영하는 중이다.

해야 할 것:

- communication/document golden dataset을 더 확장한다.
- LLM timeout, quota 초과, structured output parsing 실패 정책을 제품 플로우와 연결한다.
- LangGraph checkpoint persistence/resume은 현재 정책 metadata 수준이므로, 장기 실행 graph가 필요해지면 저장형 checkpoint를 구현한다.

### D. Human Review와 Knowledge Promotion

완료:

- Review Queue가 LLM/agent output의 trust boundary로 작동한다.
- source-less review approval rejection 테스트가 있다.
- 승인된 ReviewItem은 knowledge table로 promotion된다.
- Source Evidence Drawer가 source URL, snippet, permission, confidence, rank, AgentRun metadata를 보여준다.
- `needs_more_evidence`와 reviewer note 흐름이 있다.
- Review Queue approval은 role-aware RBAC와 연결되었다.

작업중:

- reviewer가 더 쉽게 근거를 비교하고 승인/보류할 수 있도록 UI/정보 밀도를 정리하는 단계다.

해야 할 것:

- multi-step approval states가 필요하면 `reviewer_approved`, `manager_approved`, `admin_approved`, `promoted_to_knowledge`로 확장한다.
- 낮은 confidence 항목과 evidence 부족 항목의 큐 분리를 검토한다.

### E. RAG, Vector Indexing, Knowledge Surfaces

완료:

- PostgreSQL + pgvector 방향이 정해졌고 adapter가 구현되어 있다.
- SQLite smoke mode에서는 deterministic retrieval이 유지된다.
- incremental vector indexing과 content-hash skip logic이 존재한다.
- ask/search path가 permission-aware citation과 hidden-match accounting을 제공한다.
- RAG smoke evaluation fixture가 precision, recall, hit rate를 계산한다.
- Knowledge Library, Decisions, Timeline, History, Knowledge Map 페이지가 존재한다.

작업중:

- pgvector search는 feature flag 뒤에 있으며, 기본 demo path는 zero-cost deterministic mode를 유지한다.

해야 할 것:

- production reindex는 PostgreSQL + pgvector + embedding provider key 조건에서만 허용되도록 계속 fail-closed 정책을 유지한다.
- final demo 전 permission leakage와 hidden-match regression을 다시 실행한다.

### F. Auth, RBAC, Security

완료:

- httpOnly session/refresh cookie slice가 구현되었다.
- refresh token rotation, logout revocation, demo-mode fallback이 있다.
- Google identity login과 Google data integration OAuth가 분리되었다.
- seeded admin/employee/reviewer accounts가 존재한다.
- admin user management API/UI와 audit log가 있다.
- admin-only cost observability guards가 적용되었다.

작업중:

- production auth hardening은 진행 중이다. 현재는 MVP auth/RBAC slice가 구현된 상태다.

해야 할 것:

- CSRF, rate limiting, Alembic migration hardening을 추가한다.
- Google identity provider metadata와 last-login 계열 필드를 migration으로 정리한다.
- 보안/권한 regression을 final verification에 포함한다.

### G. Frontend와 Demo UX

완료:

- Next.js App Router 기반 UI가 존재한다.
- Korean-first shell, messages, integrations, review, search, dashboard, admin, notifications, knowledge pages가 구현되어 있다.
- Knowledge Map과 approved memory pages가 demo story를 지원한다.
- AgentRun cost/detail, ranked evidence, RAG reindex approval UX가 있다.
- login/admin RBAC UI가 있다.

작업중:

- final Liquid Glass consistency pass와 portfolio recording용 화면 정리가 남아 있다.

해야 할 것:

- frontend final screenshot/clip capture를 수행한다.
- 반복 사용 화면의 loading/empty/error/unauthorized 상태를 점검한다.
- 전체 Playwright desktop/mobile smoke를 final demo 전에 다시 실행한다.

### H. Testing, CI, Deployment, Documentation

완료:

- backend test suite가 존재하며 현재 세션 검증 결과 `252 passed, 1 skipped`다.
- frontend에는 lint/build/playwright scripts가 있다.
- deployment runbook, production auth runbook, portfolio demo script, portfolio case study/log가 존재한다.
- `.env.example`이 존재한다.

작업중:

- Azure staging preparation은 design과 provider alias 수준까지 완료되었고, 실제 IaC/resource creation은 시작하지 않았다.

해야 할 것:

- 현재 환경에서는 `npm.cmd`가 없어 frontend lint/build를 재검증하지 못했다. Node/npm이 있는 환경에서 다시 실행한다.
- CI workflow가 없다면 backend test, frontend lint/build, Playwright smoke를 자동화한다.
- Azure resource creation은 예산, region, resource group, staging domain 확인 후 진행한다.

## 3. 현재 전체 코드 진행상황

### 현재 코드 기준으로 해소된 과거 감사 항목

`PROJECT_TASK_AUDIT.md`의 2026-05-04 지적 중 현재 코드 기준으로 해소되었거나 오래된 항목:

- `frontend/package.json` 충돌 마커: 현재 파일에 충돌 마커가 없다.
- `.env.example` 부재: 현재 루트 `.env.example`이 존재한다.
- `backend/main.py`와 `backend/app/main.py` 중복: 현재 `backend/main.py`는 없고 `backend/app/main.py`가 FastAPI 진입점이다.
- test file 부재: 현재 `backend/tests` 아래 test 파일 56개가 존재한다.
- search/knowledge/decisions 라우터 누락 가능성: 현재 `backend/app/api/v1/router.py`에 `search`, `knowledge` 라우터가 포함되어 있다.

### 현재 구현 밀도

- Backend: FastAPI API, SQLAlchemy models, auth/RBAC, connector ingestion, agent runtime, RAG/vector indexing, Review Queue, Knowledge API가 넓게 구현되어 있다.
- Frontend: Next.js pages와 API client가 제품형 demo 흐름을 구성한다.
- Agent runtime: Slack/Mail-Docs/RAG-Orchestrator와 Track C memory extraction boundary가 존재한다.
- Data/RAG: pgvector production path와 SQLite deterministic smoke path가 함께 유지된다.
- Cost policy: AgentRun, preflight, evidence windowing, cache/dedupe, reindex approval UX가 구현되어 있다.
- Permission policy: Review Queue, RAG hidden matches, RBAC route/API guard가 구현되어 있다.

### 현재 검증 결과

현재 세션에서 실행:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; uv run pytest backend\tests -q
```

결과:

```text
252 passed, 1 skipped
```

프론트 검증:

- `npm.cmd run lint`와 `npm.cmd run build`를 시도했으나 현재 셸에서 `npm.cmd` 명령을 찾을 수 없어 실행하지 못했다.
- Node/npm이 설치된 개발 환경에서 다음 명령을 다시 실행해야 한다.

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

### 현재 남은 핵심 리스크

- 프론트 빌드 검증이 현재 세션에서 완료되지 않았다.
- production auth는 MVP slice 이후 CSRF, rate limiting, migration hardening이 남아 있다.
- Drive/HWP/HWPX parser는 metadata-only에서 실제 문서 타입별 parsing으로 확장해야 한다.
- Azure staging은 설계와 alias까지만 완료되었고 실제 인프라 생성은 미착수다.
- final portfolio recording 전 Playwright 전체 smoke와 screenshot capture가 필요하다.

## 4. 추천 실행 순서

1. Node/npm이 있는 환경에서 frontend lint/build를 재검증한다.
2. final Playwright desktop/mobile smoke를 실행한다.
3. Drive parser run records와 file-type parser를 구현한다.
4. production auth hardening으로 CSRF, rate limiting, migration을 추가한다.
5. final portfolio screenshots/clips를 캡처한다.
6. Azure staging은 예산/region/resource group/domain 확정 후 별도 branch에서 시작한다.

