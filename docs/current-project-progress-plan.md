# ParaWorks 현재 프로젝트 진행상황

> 작성일: 2026-05-06  
> 목적: 현재 ParaWorks 프로젝트의 구현 상태, 남은 작업, 검증 상태를 한눈에 보기 위한 진행상황 문서

---

## 1. 프로젝트 요약

ParaWorks는 **한국어 우선, 근거 중심, 권한 인식형 회사 메모리 플랫폼**이다.

Slack, Gmail, Google Drive, Calendar 등 업무 도구에서 수집한 증거를 바탕으로 AI Agent가 Timeline, History, Decision, Todo 후보를 만들고, 사람이 Review Queue에서 검토한 뒤 승인된 항목만 조직 지식으로 승격한다.

현재 프로젝트는 단순 기획 단계가 아니라, **FastAPI 백엔드 + Next.js 프론트엔드 + 다중 Agent Runtime + Review Queue + RAG/pgvector 방향성 + Auth/RBAC**까지 구현된 포트폴리오형 MVP 단계다.

---

## 2. 전체 진행상황

| 영역 | 현재 상태 | 요약 |
| --- | --- | --- |
| 제품 방향 | 완료 | Evidence-first, Review Queue, 권한/비용 정책이 정리됨 |
| 백엔드 API | 진행 중 | 핵심 API는 구현됨, production hardening 필요 |
| 프론트엔드 | 진행 중 | 주요 화면 구현됨, 최종 빌드/시각 검증 필요 |
| Connector | 진행 중 | Slack/Google 계열 boundary 구현, Drive parser 고도화 필요 |
| Agent Runtime | 진행 중 | Slack, Mail/Docs, RAG/Orchestrator Agent 구현 |
| Review Queue | 진행 중 | 승인/보류/근거 확인 가능, multi-step approval은 미구현 |
| RAG/검색 | 진행 중 | deterministic smoke path와 pgvector path가 공존 |
| Auth/RBAC | 진행 중 | cookie auth, Google identity, role guard 구현, 보안 hardening 필요 |
| 테스트 | 양호 | backend test suite 통과 |
| 배포 | 준비 단계 | deployment/Azure 설계는 있음, 실제 staging은 미착수 |

---

## 3. 완료된 작업

### 3.1 제품/아키텍처

- [x] ParaWorks 제품 방향을 회사 메모리 플랫폼으로 정리
- [x] Evidence-first 원칙 정리
- [x] Review Queue를 AI output의 trust boundary로 정의
- [x] Slack Agent, Mail/Document Agent, RAG/Orchestrator Agent 3트랙 구조 정리
- [x] `backend/app/agent_runtime/`에 shared runtime contract 구현
- [x] Agent registry와 manifest boundary 구현
- [x] token cost, permission, source evidence 보존 정책 반영

### 3.2 백엔드

- [x] FastAPI 앱 구성
- [x] `/api/v1` 라우터 구성
- [x] health, auth, dashboard, integrations, review, search, ask, knowledge, notifications, agent-runs API 구현
- [x] SQLAlchemy model 구성
- [x] SQLite smoke mode 지원
- [x] PostgreSQL + pgvector 방향성 반영
- [x] Celery 기반 RAG indexing job boundary 구현

### 3.3 Connector/Ingestion

- [x] 공통 connector ingestion contract 구현
- [x] `SourceEvent`, `ConnectorManifest` boundary 구현
- [x] Slack connector boundary 구현
- [x] Slack OAuth/install/runtime status 구현
- [x] Slack selected channel sync와 incremental cursor 구현
- [x] Slack thread reply context metadata 보존
- [x] Google OAuth boundary 구현
- [x] Gmail/Drive/Calendar installed sync boundary 구현
- [x] Gmail thread/domain metadata 보존
- [x] Drive parser/version metadata 보존
- [x] Calendar attendee/status metadata 보존
- [x] connector golden dataset fixture 추가

### 3.4 Agent Runtime

- [x] Slack Agent deterministic slice 구현
- [x] Mail/Document Agent deterministic slice 구현
- [x] RAG Orchestrator Agent 구현
- [x] LangGraph company-memory orchestration foundation 구현
- [x] Timeline, History, Decision Record, Todo extraction boundary 구현
- [x] Validation gate 구현
- [x] LangChain structured-output adapter boundary 구현
- [x] Slack live LLM adapter 구현
- [x] OpenAI primary, Gemini fallback 구조 구현
- [x] paid LLM preflight, ranked evidence window, budget cap 구현

### 3.5 Review Queue/Knowledge

- [x] Review Queue API와 UI 구현
- [x] source-less ReviewItem approval rejection 구현
- [x] Source Evidence Drawer 구현
- [x] source URL, snippet, permission, confidence, rank, AgentRun metadata 표시
- [x] `needs_more_evidence`와 reviewer note workflow 구현
- [x] Review Queue 승인 시 knowledge table promotion 구현
- [x] role-aware Review Queue approval 구현

### 3.6 RAG/검색/지식 화면

- [x] `/api/v1/ask` RAG answer endpoint 구현
- [x] `/api/v1/search` retrieval endpoint 구현
- [x] permission-aware hidden match accounting 구현
- [x] RAG citation과 source snippet 반환
- [x] pgvector adapter 구현
- [x] incremental vector indexing 구현
- [x] content hash 기반 embedding skip 구현
- [x] RAG smoke evaluation fixture 구현
- [x] Knowledge Library 구현
- [x] Decisions, Timeline, History page 구현
- [x] Knowledge Map 구현

### 3.7 Auth/RBAC/Security

- [x] httpOnly session cookie 구현
- [x] refresh token table과 hashed refresh token 저장 구현
- [x] refresh token rotation 구현
- [x] logout revocation 구현
- [x] demo-mode header fallback 유지
- [x] Google identity login boundary 구현
- [x] Google identity와 Google data integration OAuth 분리
- [x] seeded admin/employee/reviewer account 구현
- [x] admin user management API/UI 구현
- [x] role-aware navigation filtering 구현
- [x] admin-only cost observability guard 구현
- [x] audit log 기록 구현

### 3.8 프론트엔드

- [x] Next.js App Router 기반 화면 구성
- [x] Korean-first workspace shell 구현
- [x] dashboard 구현
- [x] messages 구현
- [x] integrations 구현
- [x] review 구현
- [x] search/ask workbench 구현
- [x] agent-runs summary/detail 구현
- [x] knowledge, decisions, timeline, history 구현
- [x] notifications 구현
- [x] knowledge-map 구현
- [x] login/admin/RBAC UI 구현

---

## 4. 현재 작업 중인 영역

### 4.1 Connector 품질 고도화

현재 상태:

- Slack/Gmail/Drive/Calendar evidence metadata는 기본적으로 agent-ready 형태로 보존된다.
- Drive는 아직 metadata-only parser 상태에 가깝다.

진행 중인 방향:

- 실제 문서 타입별 parser 품질 개선
- Drive parser run record 추가
- HWP/HWPX parser adapter 결정
- connector별 pagination, rate limit, token refresh 검증 강화

### 4.2 Agent 품질 고도화

현재 상태:

- deterministic agent contract와 structured-output adapter가 공존한다.
- Slack live LLM path는 preflight와 cost cap 뒤에 있다.

진행 중인 방향:

- Slack/Gmail/Drive/Calendar evidence quality를 agent 입력에 더 안정적으로 반영
- communication/document golden dataset 확장
- LLM timeout, quota 초과, structured output parsing 실패 처리 정책 보강
- LangGraph checkpoint persistence/resume 필요성 검토

### 4.3 Production Auth Hardening

현재 상태:

- cookie auth, refresh rotation, Google identity login, RBAC guard는 구현되어 있다.

진행 중인 방향:

- CSRF protection 추가
- login/refresh rate limiting 추가
- production auth table Alembic migration 정리
- Google provider metadata, last login field 정리
- production mode에서 demo header가 닫히는지 검증

### 4.4 Frontend Final Polish

현재 상태:

- 주요 product page는 구현되어 있다.
- 포트폴리오 demo story를 구성할 화면은 대부분 존재한다.

진행 중인 방향:

- 전체 UI consistency pass
- loading/empty/error/unauthorized 상태 점검
- desktop/mobile Playwright smoke
- portfolio screenshot/clip capture

### 4.5 Deployment/Staging 준비

현재 상태:

- deployment runbook과 Azure integration design은 존재한다.
- `azure_openai` provider alias는 구현되어 있다.
- 실제 Azure resource creation은 아직 시작하지 않았다.

진행 중인 방향:

- staging budget, region, resource group, domain 결정
- PostgreSQL pgvector, Redis, Container Apps, Key Vault 구성 준비
- staging Playwright smoke 기준 정리

---

## 5. 남은 작업

### 5.1 우선순위 P0

- [ ] 현재 환경 또는 Node/npm이 있는 환경에서 frontend lint 실행
- [ ] 현재 환경 또는 Node/npm이 있는 환경에서 frontend build 실행
- [ ] final Playwright route regression 실행
- [ ] portfolio recording 전 screenshot/clip capture

### 5.2 우선순위 P1

- [ ] Drive file-type parser 구현
- [ ] parser run record와 parse status 저장
- [ ] HWP/HWPX parser adapter 결정
- [ ] production auth CSRF 추가
- [ ] login/refresh rate limiting 추가
- [ ] Alembic migration hardening
- [ ] multi-step approval state 필요 여부 결정
- [ ] LLM 실패/timeout/quota 정책 정리

### 5.3 우선순위 P2

- [ ] Azure staging resource 생성
- [ ] true Azure OpenAI endpoint/deployment mode 구현
- [ ] OpenTelemetry/Prometheus/Grafana 등 운영 관측성 확장
- [ ] CI workflow에 backend test, frontend lint/build, Playwright smoke 추가
- [ ] portfolio case study에 최종 screenshot과 demo 결과 반영

---

## 6. 검증 상태

### Backend

현재 세션에서 실행:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; uv run pytest backend\tests -q
```

결과:

```text
252 passed, 1 skipped
```

상태:

- backend test suite는 현재 기준 통과
- test coverage는 connector, RAG, Review Queue, RBAC, Agent Runtime, Knowledge promotion을 포함

### Frontend

현재 세션에서 시도:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

결과:

```text
npm.cmd 명령을 현재 셸에서 찾을 수 없어 실행하지 못함
```

상태:

- frontend 검증은 미완료
- Node/npm이 있는 환경에서 재실행 필요

권장 재검증:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd run test:visual -- e2e/page-regression.spec.ts
```

---

## 7. 현재 리스크

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| frontend build 미검증 | demo 직전 UI/build 실패 가능성 | Node/npm 환경에서 즉시 재검증 |
| Drive parser 미완성 | 문서 기반 history 품질 제한 | file-type parser와 parser run record 추가 |
| production auth hardening 미완료 | 배포 수준 보안 부족 | CSRF, rate limit, migration 추가 |
| Azure staging 미착수 | 실제 배포 시연 불가 | 예산/region/domain 결정 후 별도 진행 |
| final visual evidence 부족 | 포트폴리오 설득력 저하 | screenshot/clip, Playwright 결과 확보 |

---

## 8. 다음 실행 순서

1. Frontend lint/build를 Node/npm 환경에서 재실행한다.
2. Playwright route regression을 실행한다.
3. portfolio demo script 기준으로 login → integrations → agent-runs → review → knowledge → knowledge-map → search 흐름을 점검한다.
4. Drive parser와 parser run record를 구현한다.
5. production auth hardening을 진행한다.
6. final screenshot/clip을 캡처해 portfolio case study에 반영한다.
7. Azure staging은 예산과 배포 조건 확정 후 별도 branch에서 시작한다.

---

## 9. 포트폴리오 완성도를 높이기 위한 제언

현재 프로젝트는 기능 구현량이 많고, 다중 Agent/Review/RAG/권한/비용 정책까지 포함되어 있어 취업 포트폴리오로 충분히 강점이 있다. 다만 더 높은 수준의 프로젝트로 보이려면 다음을 보강하는 것이 좋다.

### 9.1 한 장짜리 Architecture Overview 추가

포트폴리오 심사자는 전체 코드를 오래 보지 않는다. 다음 흐름을 한 장의 diagram과 짧은 설명으로 정리하면 전달력이 좋아진다.

```text
Connector
  → SourceEvent
  → Agent Runtime
  → Review Queue
  → Approved Knowledge
  → RAG Answer
```

포인트:

- AI output이 곧바로 지식이 되지 않는다는 점
- 권한과 증거가 끝까지 따라간다는 점
- 비용 통제가 AgentRun과 indexing에 반영된다는 점

### 9.2 Demo Evidence Pack 만들기

`docs/demo-evidence/` 같은 폴더를 만들어 다음 자료를 모으면 좋다.

- backend test 결과 캡처
- frontend build 결과 캡처
- Playwright 결과 캡처
- Review Queue evidence drawer screenshot
- Knowledge Map screenshot
- RAG answer citation screenshot
- AgentRun cost observability screenshot

이 자료는 면접에서 "실제로 어디까지 만들었는지"를 빠르게 증명한다.

### 9.3 품질 지표를 수치로 보여주기

현재 RAG smoke evaluation이 있으므로, 포트폴리오에는 다음 수치를 보여주는 것이 좋다.

- RAG precision@k
- recall@k
- hidden restricted match count
- indexed/skipped vector count
- saved embedding calls
- AgentRun estimated cost
- cache hit count

단순히 "RAG를 구현했다"보다 "비용과 품질을 측정했다"가 훨씬 강하게 보인다.

### 9.4 Production Readiness Checklist를 완료형으로 만들기

배포를 실제로 하지 않더라도, 아래 항목이 체크된 문서를 만들면 프로젝트 수준이 올라간다.

- secrets는 git에 없음
- demo auth와 production auth 분리
- restricted source leakage test 있음
- paid LLM call은 preflight 필요
- embedding reindex는 dry-run 필요
- rollback plan 있음
- staging 환경 변수 표 있음

### 9.5 “왜 이 구조가 필요한가”를 case study에 더 명확히 쓰기

기술 나열보다 문제 해결 구조를 강조하는 것이 좋다.

좋은 설명 구조:

1. 문제: Slack/Gmail/Drive에 의사결정 맥락이 흩어짐
2. 위험: AI가 출처 없이 답하면 업무 지식으로 신뢰할 수 없음
3. 해결: EvidencePacket → Review Queue → Approved Knowledge
4. 보강: permission filter, cost cap, cache, pgvector
5. 결과: 검색 가능한 회사 기억과 감사 가능한 AI 실행 기록

### 9.6 Final Demo는 “기능 목록”이 아니라 “업무 시나리오”로 구성하기

추천 demo 시나리오:

1. Slack/Gmail/Drive evidence가 수집된다.
2. Agent가 의사결정 후보를 만든다.
3. Reviewer가 source evidence를 열어본다.
4. Reviewer가 승인한다.
5. 승인된 내용이 Decision/Timeline/History에 나타난다.
6. 사용자가 자연어로 질문한다.
7. RAG가 citation과 permission notice를 포함해 답한다.
8. Admin이 AgentRun cost와 token usage를 확인한다.

이 흐름이 녹화되면 취업 포트폴리오에서 “완성된 제품형 프로젝트”로 보이기 쉽다.

