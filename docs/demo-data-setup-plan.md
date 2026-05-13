# ParaWorks 데모 데이터 구축 계획

ParaWorks 포트폴리오 데모를 위해 Gmail과 Google Drive에 실제로 존재해야 할
데이터의 목록과 작성 지침을 정의한다.

데모 목표:
- "우리 메일/드라이브에서 어떤 논의가 있었고, 무엇이 결정되었는가?"
- "회사 문서에 어떤 내용이 들어있는가?"
- 이 두 질문에 ParaWorks가 근거를 가지고 답하는 흐름을 5분 안에 시연한다.

---

## 1. 회사 시나리오

**회사명**: ParaWorks Inc.
**업종**: B2B AI SaaS 스타트업 (회사 기억 플랫폼)
**현재 단계**: 초기 제품 완성 후 첫 엔터프라이즈 고객 파일럿 + 시드 투자 유치 병행

### 구성원 정의

| 이름 | 계정 | 시스템 역할 | 직함 | 데모 방식 |
|:---|:---|:---|:---|:---|
| 한승헌 (Han Seunghun) | hanvv3@gmail.com | admin | CEO / Co-Founder | 실제 데모 계정 |
| 김종우 (Kim Jongwoo) | kjw4work@gmail.com | admin | COO | 실제 데모 계정 |
| 김용희 (Kim Yonghee) | yonghee199702@gmail.com | admin | CTO | 실제 데모 계정 |
| 한준혁 (Han Junhyuk) | hanvv3@koreacu.ac.kr | employee | AI Agent Developer | CC 전용 가상 인물 |
| 김미나 (Kim Mina) | mina@paraworks.com | reviewer | Product Manager | CC 전용 가상 인물 |

> 권한 참고:
> - admin 3명: public / internal / restricted 전체 접근
> - employee (한준혁): public / internal 만 접근 → restricted 문서 hidden match 데모
> - reviewer (김미나): public / internal 만 접근 → Review Queue 승인 담당

---

## 2. 프로젝트 시나리오 (2개)

### Project A: 첫 엔터프라이즈 파일럿 계약 (K테크 솔루션즈)

**기간**: 2026년 3월 ~ 5월 (현재 진행형)
**담당**: 김종우(COO) 주도, 김용희(CTO) 기술 지원, 김미나(PM) CC 참조
**핵심 이벤트**: K테크 솔루션즈와 3개월 파일럿 계약 체결 → 5월 18일 온보딩 시작

결정사항 후보:
- "K테크 파일럿 계약 3개월 / 월 200만원 조건으로 최종 확정 (2026-05-13)"
- "온보딩 시작 전 보안 서약서(NDA) 체결 완료 필수"
- "파일럿 성공 지표: 30일 이내 Review Queue 승인율 70% 이상"

### Project B: 시드 투자 IR (Series Seed)

**기간**: 2026년 4월 ~ 6월 (진행 중)
**담당**: 한승헌(CEO) 주도, 김종우(COO), 김용희(CTO) 공동 참여
**핵심 이벤트**: 시드 투자 목표 15억 설정 → 주요 VC 미팅 진행 중 (5월 10일~18일)

결정사항 후보:
- "시드 라운드 목표 투자금 15억원으로 상향 조정 (2026-05-12)"
- "Pre-money valuation 70억 기준으로 VC 미팅 진행"
- "재무 프로젝션 문서는 restricted로 관리, 공개 IR 데크와 분리"

---

## 3. Google Drive 구축 계획

### 폴더 구조

```
ParaWorks Drive /
├── 00_회사규정/
│   ├── 온보딩_가이드.md
│   ├── 보안_정책_v1.0.docx
│   └── 정보보호_서약서_템플릿.docx
├── 01_제품_기술/
│   ├── ParaWorks_기술_개요.md
│   ├── API_설계서_v1.md
│   └── 배포_런북.md
├── 02_파일럿_프로젝트/    ← Project A
│   ├── K테크_파일럿_제안서_v1.docx
│   ├── K테크_파일럿_제안서_v2.docx
│   ├── 파일럿_성공지표_정의서.md
│   ├── 고객_온보딩_체크리스트.md
│   └── K테크_NDA_초안.docx          ← restricted
├── 03_IR_투자/    ← Project B
│   ├── ParaWorks_IR_데크_v1.pdf          ← restricted
│   ├── ParaWorks_IR_데크_v2.pdf          ← restricted
│   ├── 재무_프로젝션_2026.docx            ← restricted
│   ├── 시장_분석_보고서.pdf
│   └── VC_미팅_메모.md                    ← restricted
└── 04_회의록/
    ├── 2026-03-15_파일럿전략_회의.md
    ├── 2026-04-05_IR전략_킥오프.md
    ├── 2026-05-11_K테크_최종조율.md
    ├── 2026-05-13_VC미팅_메모_A벤처스.md       ← restricted
    ├── 2026-05-15_온보딩_준비회의.md
    └── 2026-05-18_데모_및_온보딩_킥오프.md
```

### 주요 문서 내용 지침

#### [온보딩_가이드.md] — text/markdown → parsed ✅
- 입사 첫 날 절차: 슬랙 가입, Google Drive 권한 요청, 노션 계정 생성
- 주요 연락처 (CEO/COO/CTO 직통)
- "모르는 것은 #general 채널에 질문하세요"
- **데모 질문**: "온보딩 절차가 뭐야?" → RAG 답변

#### [ParaWorks_기술_개요.md] — text/markdown → parsed ✅
- ParaWorks가 해결하는 문제: 회사 기억 분산 문제
- 핵심 기능: Slack/Gmail/Drive 통합, Review Queue, 권한 인지형 RAG
- 기술 스택: FastAPI, LangGraph, pgvector, Next.js
- **데모 질문**: "ParaWorks가 어떤 기술을 쓰나요?" → RAG 답변

#### [K테크_파일럿_제안서_v2.docx] — docx → parsed ✅
- v1에서 변경사항: 파일럿 기간 1개월 → 3개월, 성공 지표 추가
- 제안 금액: 월 150만원 × 3개월
- 성공 기준 명시
- **데모 활용**: 버전 추적(v1→v2) + Review Queue 결정사항 근거

#### [파일럿_성공지표_정의서.md] — text/markdown → parsed ✅
- 정량 지표: 30일 이내 Review Queue 승인율 60% 이상
- 정성 지표: 팀장급 사용자 만족도 4점 이상(5점 만점)
- 측정 주기: 격주 체크인 미팅

#### [재무_프로젝션_2026.docx] — docx → parsed ✅, **permission: restricted**
- 2026년 ARR 목표: 5억원
- 고객사별 예상 매출 분해
- Burn rate 및 런웨이 계산
- **데모 활용**: employee/reviewer 계정으로 검색 시 hidden match 시연

#### [VC_미팅_메모.md] — text/markdown → parsed ✅, **permission: restricted**
- 미팅 일시, VC 담당자명, 주요 질의응답 메모
- "팀 구성 완성도 지적 → CTO 레퍼런스 추가 검토 필요"
- **데모 활용**: restricted 권한 필터링 시연

#### [2025-11-05_IR전략_킥오프.md] — text/markdown → parsed ✅
```
날짜: 2025-11-05
참석자: 한병우(CEO), 김종우(COO), 김용희(CTO)
CC 참조: 한준혁(koreacu)

안건 1. IR 목표 설정
- 한병우: 시드 라운드 목표 10억, Pre-money 50억 기준 제안
- 김종우: 현재 Burn rate 기준 18개월 런웨이 확보 필요
- 결정: 목표 투자금 10억, Pre-money valuation 50억으로 확정

안건 2. IR 자료 구성
- 김용희: 기술 차별화 슬라이드 직접 작성
- 재무 프로젝션 문서는 restricted로 관리
- 결정: 공개 IR 데크와 내부 재무 문서 분리 관리

액션 아이템:
- 한병우: 11/12까지 IR 데크 v1 초안 작성
- 김종우: 11/10까지 재무 프로젝션 작성
- 김용희: 11/15까지 기술 슬라이드 초안 작성
```

---

## 4. Gmail 구축 계획

### Thread 목록

#### Thread 1 — Project A: 파일럿 제안 논의 시작
**날짜**: 2026-03-15
**참여자**: kjw4work@gmail.com → yonghee199702@gmail.com, CC: mina@paraworks.com
**제목**: `[논의] K테크 솔루션즈 파일럿 제안 검토 요청`

```
메일 1 (COO → CTO, CC: PM):
K테크 솔루션즈 측에서 파일럿에 관심을 보이고 있습니다.
기술적으로 1개월 파일럿이 가능한지 검토 부탁드립니다.

메일 2 (CTO → COO):
1개월은 짧습니다. 3개월은 되어야 데이터가 쌓입니다.
성공 지표도 승인율 70% 정도로 잡아야 합니다.

메일 3 (COO → CTO):
알겠습니다. 3개월 조건으로 제안서 업데이트합니다.
```

#### Thread 2 — Project A: 최종 계약 승인 (최근)
**날짜**: 2026-05-12 ~ 2026-05-13
**참여자**: kjw4work@gmail.com → hanvv3@gmail.com, CC: mina@paraworks.com
**제목**: `[긴급] K테크 파일럿 최종 계약 조건 확정 및 승인 요청`

```
메일 1 (COO → CEO, CC: PM):
K테크 측과 월 200만원, 3개월 조건으로 최종 조율되었습니다.
5월 18일 월요일부터 온보딩 시작하기로 했습니다. 승인 부탁드립니다.

메일 2 (CEO → COO):
조건 좋습니다. 승인하니 계약 체결 진행하세요.
5월 18일 데모 데이와 겹치니 준비 잘 부탁드립니다.
```

#### Thread 3 — Project B: VC 미팅 팔로업 (최근)
**날짜**: 2026-05-14
**참여자**: hanvv3@gmail.com → kjw4work@gmail.com, yonghee199702@gmail.com
**제목**: `[IR] A벤처스 미팅 결과 공유 및 액션 아이템`

```
메일 1 (CEO → COO, CTO):
오늘 A벤처스 미팅 분위기 좋았습니다.
특히 '권한 인지형 RAG' 부분에 큰 관심을 보였습니다.
추가로 요청한 재무 프로젝션 2026 업데이트 버전 전달 부탁합니다.

메일 2 (COO → CEO):
재무 프로젝션 업데이트 중입니다. 내일 오전까지 마무리해서 공유하겠습니다.
해당 문서는 기밀(restricted)로 관리하겠습니다.
```

#### Thread 4 — Project A/B: 데모 데이 준비 현황 체크
**날짜**: 2026-05-16 ~ 2026-05-17
**참여자**: hanvv3@gmail.com → 전체
**제목**: `[공지] 5월 18일 데모 데이 및 K테크 온보딩 최종 점검`

```
메일 1 (CEO → 전체):
드디어 이번 주 월요일이 데모 데이입니다.
K테크 온보딩과 동시에 투자자 대상 제품 시연이 예정되어 있습니다.
마지막까지 데이터 정합성 및 권한 설정 체크 바랍니다.

메일 2 (CTO → CEO):
기술팀 준비 완료되었습니다. pgvector 인덱싱 상태와 
Review Queue 시나리오 모두 점검 마쳤습니다.

메일 3 (PM → 전체):
온보딩 가이드와 데모용 시나리오 문서 Drive에 최종 업로드했습니다.
```

> **권한 설정**: Thread 5 전체와 첨부 PDF → `permission_level='restricted'`
> **데모 활용**: hanvv3@koreacu.ac.kr (employee) 계정으로 "IR 데크" 검색 시 hidden match 시연

---

## 5. Google Calendar 구축 계획

| 날짜 | 이벤트 | 참석자 |
|:---|:---|:---|
| 날짜 | 이벤트 | 참석자 |
|:---|:---|:---|
| 2026-03-15 | K테크 파일럿 초기 전략 회의 | 한승헌, 김종우, 김용희 |
| 2026-04-05 | IR 전략 킥오프 미팅 | 한승헌, 김종우, 김용희 |
| 2026-05-11 | K테크 최종 조율 회의 | 김종우, 김미나 |
| 2026-05-13 | A벤처스 투자 미팅 | 한승헌, 김종우 |
| 2026-05-15 | 데모 및 온보딩 준비 회의 | 전 사원 |
| 2026-05-18 | **ParaWorks 서비스 데모 데이** | 전 사원 + 외부 인사 |

---

## 6. 데모 시연 흐름 (5분 스크립트)

### Step 1. 연동 확인 (30초)
- `/integrations`에서 Gmail, Drive, Calendar 연결 상태 확인

### Step 2. 동기화 실행 (30초)
- Drive Sync → fetched/created/skipped 결과 확인
- Gmail Sync 실행
- `/documents`에서 `parsed` 문서 목록 확인 (MD, DOCX, PDF 모두 포함)

### Step 3. Agent Review 실행 (1분)
- Mail/Document Agent Review 실행
- `/review`에서 `pending_review` 항목 확인
  - "K테크 파일럿 3개월 확정" 결정사항 후보
  - "IR 목표 10억 확정" 결정사항 후보
- Source Evidence Drawer로 이메일 스레드 + 제안서 근거 제시

### Step 4. 검토 및 승인 (1분)
- 리뷰어(admin)가 결정사항 항목 승인
- `/knowledge` Decisions 페이지에서 승인된 내용 확인

### Step 5. RAG 답변 시연 (1분 30초)
- "K테크 파일럿 계약 조건이 뭐야?"
  → Thread 3 + 제안서 v2 + 회의록이 citation으로 제시
- "온보딩할 때 뭘 해야 하나요?"
  → 온보딩_가이드.md 내용 인용
- "ParaWorks IR 목표 투자금이 얼마야?"
  → Thread 4 + IR 킥오프 회의록 근거 제시

### Step 6. 권한 필터링 시연 (30초)
- hanvv3@koreacu.ac.kr (employee) 계정으로 로그인
- "IR 데크 내용 보여줘" 검색
  → "접근 권한 없는 문서 있음 (hidden: 2)" — 내용 노출 없음

---

## 7. 파서 상태 요약

| 파일 유형 | MIME 타입 | 예상 parser_status |
|:---|:---|:---|
| `.md` 회의록/가이드 | text/markdown | ✅ parsed |
| `.docx` 제안서/보안정책 | application/vnd.openxml... | ✅ parsed |
| `.pdf` IR 데크/시장 분석 | application/pdf | ✅ parsed |

---

## 8. 데이터 구축 체크리스트

### Google Drive
- [ ] `00_회사규정/온보딩_가이드.md`
- [ ] `00_회사규정/보안_정책_v1.0.docx`
- [ ] `00_회사규정/정보보호_서약서_템플릿.docx`
- [ ] `01_제품_기술/ParaWorks_기술_개요.md`
- [ ] `01_제품_기술/API_설계서_v1.md`
- [ ] `01_제품_기술/배포_런북.md`
- [ ] `02_파일럿_프로젝트/K테크_파일럿_제안서_v1.docx`
- [ ] `02_파일럿_프로젝트/K테크_파일럿_제안서_v2.docx`
- [ ] `02_파일럿_프로젝트/파일럿_성공지표_정의서.md`
- [ ] `02_파일럿_프로젝트/고객_온보딩_체크리스트.md`
- [ ] `02_파일럿_프로젝트/K테크_NDA_초안.docx` *(restricted)*
- [ ] `03_IR_투자/ParaWorks_IR_데크_v1.pdf` *(restricted)*
- [ ] `03_IR_투자/ParaWorks_IR_데크_v2.pdf` *(restricted)*
- [ ] `03_IR_투자/재무_프로젝션_2026.docx` *(restricted)*
- [ ] `03_IR_투자/시장_분석_보고서.pdf`
- [ ] `03_IR_투자/VC_미팅_메모.md` *(restricted)*
- [ ] `04_회의록/2025-10-08_파일럿전략_회의.md`
- [ ] `04_회의록/2025-11-05_IR전략_킥오프.md`
- [ ] `04_회의록/2025-11-19_K테크_2차미팅.md`
- [ ] `04_회의록/2025-12-03_IR데크_검토회의.md`
- [ ] `04_회의록/2025-12-15_파일럿_최종확정.md`

### Gmail (3개 실 계정 + 2개 가상 CC)
- [ ] Thread 1: 파일럿 제안 논의 시작 (3 메시지)
- [ ] Thread 2: 제안서 v2 검토 + DOCX 첨부 (3 메시지)
- [ ] Thread 3: 파일럿 계약 최종 확정 (2 메시지)
- [ ] Thread 4: IR 전략 논의 (3 메시지)
- [ ] Thread 5: IR 데크 검토 + PDF 첨부 *(restricted)* (3 메시지)

### Google Calendar
- [ ] 6개 이벤트 생성 (섹션 5 참조)

### 연동 및 검증
- [ ] 3개 실 계정 Google OAuth 연결 완료
- [ ] Drive Sync / Gmail Sync 결과 스크린샷 캡처
- [ ] `/documents` parsed 문서 수 확인
- [ ] Agent Review → 결정사항 후보 2개 이상 확인
- [ ] 5분 데모 스크립트 질문 3개 정상 답변 확인
- [ ] employee 계정(koreacu) restricted 필터링 확인

---

## 9. 주의사항

1. **실제 민감 정보 금지**: 데모 계정은 실제 재무/법적 정보를 담지 않는 가상 수치를 사용한다.
2. **OAuth 토큰 보안**: `.env` 파일에만 저장하고 커밋하지 않는다.
3. **첨부파일 중복 활용**: Gmail 첨부와 Drive 파일이 동일 파일이면 같은 content_signature로 dedupe 데모가 가능하다.
4. **버전 파일 유지**: 제안서 v1/v2, IR 데크 v1/v2는 모두 Drive에 있어야 Document Version 추적 데모가 가능하다.
5. **Mock 모드 확인**: 실제 Google 연동 시 `.env`의 `PARAWORKS_DEMO_MODE=false` 확인 필수.

---

*작성일: 2026-05-13 | 관련 문서: `docs/document-agent-verification-procedure.md`*
