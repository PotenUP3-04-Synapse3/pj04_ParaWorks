# Google Demo Mail Calendar Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 2026년 5월 한 달 동안 바쁜 COO의 업무 흐름을 보여주는 Gmail 메일 스레드와 Google Calendar 일정을 준비해 ParaWorks 데모에서 Gmail/Calendar 근거, Review Queue, Dashboard, Projects/Timeline, AI 비서 검색 흐름을 시연한다.

**Architecture:** 실제 Google 계정에 안전하게 더미 데이터를 쓰고, ParaWorks의 Google sync가 이를 `Source` 근거로 수집하게 한다. 메일과 일정은 모두 한승헌, 김용희, 김종우(COO)를 중심으로 구성하되, AI 출력은 Review Queue 승인 전 trusted knowledge로 취급하지 않는다.

**Tech Stack:** Gmail, Google Calendar, ParaWorks Google OAuth sync, FastAPI connector ingestion, Mail/Document/Calendar Agent, Review Queue, Projects/Timeline, Dashboard.

---

## 범위

- 기간: 2026-05-01 금요일부터 2026-05-31 일요일까지, Asia/Seoul 기준.
- 주인공: 김종우 COO `kjw4work@gmail.com`.
- 핵심 관계자:
  - 한승헌 CEO `hanvv3@gmail.com`
  - 김용희 CTO `yonghee199702@gmail.com`
- 보조 참조자:
  - 한준혁 AI Agent Developer `hanvv3@koreacu.ac.kr`
  - 김미나 Product Manager: 문서상 역할로만 사용하고, `@paraworks.com` 주소로는 메일을 보내거나 일정 초대하지 않는다.
- 프로젝트 축:
  - Project A: K테크 엔터프라이즈 파일럿 계약
  - Project B: 시드 투자 IR
- 제외: 실제 고객명, 실제 재무정보, 실제 법무 문서, 실제 개인 일정.

## 데이터 설계 원칙

- 모든 내용은 더미 데이터임을 내부적으로 관리하고, 실제 민감정보를 넣지 않는다.
- `@paraworks.com` 도메인은 가상의 회사 도메인이므로 Gmail 수신자, CC, Calendar 참석자에 절대 넣지 않는다.
- 김미나 PM은 데모 시나리오의 역할명으로만 언급하고, 실제 초대/발송 대상에서는 제외한다.
- Gmail은 스레드 단위로 자연스럽게 이어지게 작성한다. 후속 메일은 반드시 Reply로 보낸다.
- Calendar는 COO가 바쁜 사람처럼 보이도록 하루 3~6개 업무 일정을 배치하되, 데모 질문에 답할 수 있는 명확한 결정/할 일/근거를 포함한다.
- Calendar 설명에는 짧은 근거 문장을 넣는다. 예: `결정: K테크 파일럿 조건은 3개월 / 월 200만원 기준으로 검토`.
- restricted 시연용 항목은 제목과 설명에 `[기밀]` 또는 `[restricted]`를 붙이고, 외부 CC를 넣지 않는다.
- ParaWorks가 좋은 후보를 만들 수 있도록 일정 제목과 메일 본문에 프로젝트명, 날짜, 결정사항, 담당자, 다음 액션을 명확히 쓴다.

## Task 1: 계정과 권한 확인

**Files:** 없음

- [ ] **Step 1: Google 계정 역할 확인**

확인할 계정:

| 역할 | 이름 | 이메일 | 목적 |
| --- | --- | --- | --- |
| COO | 김종우 | `kjw4work@gmail.com` | 일정 밀도와 업무 지시의 중심 계정 |
| CEO | 한승헌 | `hanvv3@gmail.com` | 최종 승인, IR 의사결정 |
| CTO | 김용희 | `yonghee199702@gmail.com` | 기술 검토, 구현 일정 |
| Developer | 한준혁 | `hanvv3@koreacu.ac.kr` | CC/참석자, 권한 제한 시연 |
| PM | 김미나 | 발송/초대 금지 | 문서상 온보딩/요구사항 담당 역할 |

- [ ] **Step 2: ParaWorks Google OAuth 연결 상태 확인**

ParaWorks `/integrations`에서 Gmail과 Google Calendar가 연결되어 있는지 확인한다.

필수 조건:

- Gmail read/sync 권한이 있어야 한다.
- 실제 Gmail 발송까지 ParaWorks AI 비서로 시연하려면 `gmail.send` 권한이 필요하다.
- Calendar sync는 `paraworks-mng` 캘린더를 읽을 수 있어야 한다.
- Google Calendar에서 `paraworks-mng` 캘린더가 생성되어 있고, 일정 추가 권한이 있는지 확인한다.

- [ ] **Step 3: 쓰기 방식 결정**

권장 방식:

- Calendar 일정 생성: Google Calendar UI 또는 Calendar API.
- Gmail 발송: 실제 Gmail UI에서 수동 발송. 자동 발송은 오발송 위험이 있으므로 최종 승인 후에만 진행한다.
- Gmail 수신자/CC에는 `hanvv3@gmail.com`, `kjw4work@gmail.com`, `yonghee199702@gmail.com`, `hanvv3@koreacu.ac.kr`만 사용한다.

## Task 2: 5월 Calendar 일정 생성

**Files:** 없음

- [ ] **Step 1: Calendar 공통 설정**

모든 일정 공통값:

- Timezone: `Asia/Seoul`
- Calendar target: `paraworks-mng`
- Calendar owner: `paraworks-mng` 캘린더에 쓰기 권한이 있는 Google 계정
- Attendees: `hanvv3@gmail.com`, `kjw4work@gmail.com`, `yonghee199702@gmail.com`, `hanvv3@koreacu.ac.kr`만 사용한다. `@paraworks.com` 주소는 초대하지 않는다.
- Visibility:
  - 일반 업무: default/internal
  - IR 재무/투자: private 또는 제목에 `[기밀]`
- Description format:

```text
ParaWorks 데모 더미 일정입니다.
프로젝트: [K테크 파일럿 계약 또는 시드 투자 IR]
목적: [짧은 목적]
결정/근거: [확정 또는 논의된 사실]
다음 액션: [담당자와 기한]
```

- [ ] **Step 2: 2026-05-01 ~ 2026-05-10 초기 조율 일정 추가**

| 날짜 | 시간 | 제목 | 참석자 | 설명 핵심 |
| --- | --- | --- | --- | --- |
| 2026-05-01 | 09:30-10:00 | COO 주간 우선순위 정리 | 김종우 | 5월 데모, K테크, IR 병행 관리 |
| 2026-05-01 | 14:00-15:00 | K테크 파일럿 조건 재검토 | 김종우, 김용희 | 3개월 파일럿과 성공지표 확인 |
| 2026-05-04 | 10:00-10:45 | CEO/COO 5월 운영 리스크 점검 | 한승헌, 김종우 | 데모 전 승인 항목 정리 |
| 2026-05-04 | 16:00-17:00 | CTO 구현 일정 확인 | 김종우, 김용희 | Calendar/Gmail 근거 동기화 확인 |
| 2026-05-06 | 11:00-12:00 | K테크 보안/NDA 체크 | 김종우, 김용희 | 온보딩 전 NDA 필수 |
| 2026-05-08 | 15:00-16:00 | IR 스토리라인 리뷰 | 한승헌, 김종우, 김용희 | 권한 인식 RAG 강조 |

- [ ] **Step 3: 2026-05-11 ~ 2026-05-17 집중 업무 일정 추가**

| 날짜 | 시간 | 제목 | 참석자 | 설명 핵심 |
| --- | --- | --- | --- | --- |
| 2026-05-11 | 09:00-09:30 | COO 데일리 플래닝 | 김종우 | 바쁜 일정 시작점 |
| 2026-05-11 | 10:00-11:00 | K테크 최종 조율 회의 | 김종우, 한승헌 | 계약 조건 최종 확인 |
| 2026-05-12 | 13:00-14:00 | CEO 승인 요청: K테크 계약 | 한승헌, 김종우 | 3개월 / 월 200만원 승인 요청 |
| 2026-05-13 | 10:00-11:00 | A벤처 투자 미팅 준비 | 한승헌, 김종우, 김용희 | IR 질문 예상 답변 정리 |
| 2026-05-13 | 16:00-17:00 | [기밀] IR 재무 슬라이드 리뷰 | 한승헌, 김종우, 김용희 | restricted 시연용 |
| 2026-05-14 | 11:00-12:00 | A벤처 미팅 결과 공유 | 한승헌, 김종우, 김용희 | 권한 인식 RAG 관심 확인 |
| 2026-05-15 | 09:30-10:30 | ParaWorks 데모 데이터 점검 | 한승헌, 김종우, 김용희, 한준혁 | Gmail/Calendar sync 전 최종 체크 |
| 2026-05-15 | 15:00-16:00 | K테크 온보딩 일정 확정 | 김종우, 김용희 | 2026-05-18 시작 준비 |

- [ ] **Step 4: 2026-05-18 ~ 2026-05-31 후속 실행 일정 추가**

| 날짜 | 시간 | 제목 | 참석자 | 설명 핵심 |
| --- | --- | --- | --- | --- |
| 2026-05-18 | 10:00-11:30 | K테크 파일럿 킥오프 | 김종우, 김용희, 한준혁 | 온보딩 시작 |
| 2026-05-18 | 16:00-16:30 | COO 후속 액션 정리 | 김종우 | Review Queue 승인 대상 확인 |
| 2026-05-20 | 13:00-14:00 | K테크 성공지표 중간 점검 | 김종우, 김용희 | Review Queue 승인율 70% 목표 |
| 2026-05-21 | 10:00-11:00 | [기밀] IR 투자자 Q&A 리허설 | 한승헌, 김종우, 김용희 | restricted 검색 시연용 |
| 2026-05-22 | 17:00-18:00 | COO 주간 리포트 작성 | 김종우 | 한승헌에게 메일 발송 예정 |
| 2026-05-25 | 11:00-12:00 | K테크 1주차 리스크 리뷰 | 김종우, 김용희 | 기술 리스크와 고객 피드백 |
| 2026-05-27 | 14:00-15:00 | IR 후속자료 버전 확정 | 한승헌, 김종우, 김용희 | IR deck v2.1 |
| 2026-05-29 | 09:30-10:30 | 5월 회사 메모리 회고 | 한승헌, 김종우, 김용희, 한준혁 | ParaWorks가 근거를 잘 회수하는지 점검 |

## Task 3: Gmail 스레드 작성

**Files:** 없음

- [ ] **Step 1: 메일 스레드 공통 규칙**

모든 메일은 실제 Gmail에서 발송한다.

- 첫 메일은 새 메일로 작성한다.
- 후속 메일은 반드시 같은 스레드에서 Reply로 작성한다.
- 본문 말미에 `다음 액션:`을 넣는다.
- 데모 더미임을 외부로 보내지 않도록 수신자를 위 계정으로만 제한한다.
- `@paraworks.com` 주소는 가상 도메인이므로 To/CC/BCC에 넣지 않는다.

- [ ] **Step 2: Thread A1 - K테크 조건 확정**

Subject: `[K테크] 파일럿 계약 조건 최종 확인`

발송 순서:

1. 2026-05-11 10:30, COO 김종우 -> CEO 한승헌
2. 2026-05-12 09:20, CEO 한승헌 -> COO 김종우
3. 2026-05-12 13:40, COO 김종우 -> CTO 김용희, CC 한준혁

핵심 내용:

- K테크 파일럿은 3개월, 월 200만원 기준.
- 시작 예정일은 2026-05-18.
- NDA 완료 후 온보딩 진행.
- 김용희는 기술 온보딩 체크리스트를 2026-05-15까지 정리.

- [ ] **Step 3: Thread A2 - 기술 온보딩 준비**

Subject: `[K테크] 온보딩 기술 준비 및 성공지표 확인`

발송 순서:

1. 2026-05-13 15:00, COO 김종우 -> CTO 김용희
2. 2026-05-14 10:20, CTO 김용희 -> COO 김종우
3. 2026-05-15 14:10, COO 김종우 -> CTO 김용희, CC CEO 한승헌

핵심 내용:

- 성공지표: 30일 내 Review Queue 승인율 70% 이상.
- Calendar/Gmail/Drive 근거 수집 품질 점검.
- 2026-05-18 킥오프 전 테스트 계정과 권한 확인.

- [ ] **Step 4: Thread B1 - IR 미팅 결과 공유**

Subject: `[IR] A벤처 미팅 결과 및 후속자료 요청`

발송 순서:

1. 2026-05-14 12:30, CEO 한승헌 -> COO 김종우, CTO 김용희
2. 2026-05-14 16:30, COO 김종우 -> CEO 한승헌, CC CTO 김용희
3. 2026-05-15 11:00, CTO 김용희 -> CEO 한승헌, CC COO 김종우

핵심 내용:

- A벤처가 권한 인식 RAG와 회사 메모리 근거 추적에 관심.
- COO는 재무 슬라이드 수치를 업데이트.
- CTO는 pgvector 기반 검색과 hidden match 설명을 보강.

- [ ] **Step 5: Thread B2 - restricted 권한 시연용**

Subject: `[기밀][IR] 재무 슬라이드 v2.1 수정 범위`

발송 순서:

1. 2026-05-21 09:00, COO 김종우 -> CEO 한승헌, CTO 김용희
2. 2026-05-21 15:00, CEO 한승헌 -> COO 김종우, CTO 김용희

핵심 내용:

- 재무 문서는 restricted로 관리.
- 외부 공유용 IR deck과 내부 재무 projection을 분리.
- 한준혁은 CC에 넣지 않는다. `@paraworks.com` 주소도 넣지 않는다.

- [ ] **Step 6: Thread C1 - 5월 회고와 데모 점검**

Subject: `[운영] 5월 ParaWorks 데모 데이터 및 일정 회고`

발송 순서:

1. 2026-05-29 11:00, COO 김종우 -> CEO 한승헌, CTO 김용희, CC 한준혁
2. 2026-05-29 16:00, CEO 한승헌 -> COO 김종우, CTO 김용희, CC 한준혁

핵심 내용:

- 5월 Gmail/Calendar 근거가 Dashboard, Review Queue, Timeline에서 보이는지 확인.
- 데모 질문 3개를 확정한다.
- 다음 액션: Review Queue 승인 후 AI 비서 검색 시연.

## Task 4: ParaWorks 동기화와 검토

**Files:** 없음

- [ ] **Step 1: Gmail/Calendar 동기화 실행**

ParaWorks `/integrations`에서 다음 순서로 실행한다.

1. Google Calendar sync
2. Gmail sync
3. Drive sync가 필요한 경우 Drive sync

기대 결과:

- sync job이 `complete` 상태가 된다.
- fetched, created, skipped count가 보인다.
- Calendar source 중 `calendar_summary` 또는 캘린더 식별자가 `paraworks-mng`로 확인된다.
- 같은 데이터를 다시 sync하면 skipped count가 증가하거나 created count가 줄어든다.

- [ ] **Step 2: Dashboard 확인**

`/dashboard`에서 확인한다.

- 오늘 일정 패널에 2026-05-15 기준 일정이 보인다.
- COO 계정으로 로그인했을 때 바쁜 일정 흐름이 자연스럽다.
- Calendar 원천 이벤트는 trusted knowledge가 아니라 schedule visibility로만 보인다.

- [ ] **Step 3: Review Queue 확인**

`/review`에서 확인한다.

- Gmail/Calendar 기반 pending review 후보가 생성된다.
- 후보에는 source URL, snippet, permission level, confidence가 있다.
- restricted 메일/일정은 restricted permission을 유지한다.

- [ ] **Step 4: 승인 후 Project/Timeline 확인**

관리자 계정으로 주요 후보를 승인한다.

우선 승인 후보:

- K테크 파일럿 조건 확정
- K테크 온보딩 시작일 2026-05-18
- IR 후속자료 v2.1 수정 필요
- 재무 문서 restricted 관리

확인 화면:

- `/projects`
- `/timeline`
- `/search`

## Task 5: 데모 질문 준비

**Files:** 없음

- [ ] **Step 1: COO 일정 질문**

질문:

```text
5월 15일 김종우 COO 일정 중 K테크와 관련된 회의가 뭐였어?
```

기대 답:

- ParaWorks 데모 데이터 점검
- K테크 온보딩 일정 확정
- Calendar 근거 링크/스니펫 표시

- [ ] **Step 2: K테크 의사결정 질문**

질문:

```text
K테크 파일럿 계약 조건과 시작일이 어떻게 확정됐어?
```

기대 답:

- 3개월 / 월 200만원
- 2026-05-18 시작
- Gmail Thread A1과 Calendar 회의 근거 표시

- [ ] **Step 3: IR 권한 필터 질문**

관리자 계정 질문:

```text
IR 재무 슬라이드 v2.1에서 수정하기로 한 내용이 뭐야?
```

직원 계정 질문:

```text
IR 재무 슬라이드 v2.1 내용을 보여줘.
```

기대 결과:

- 관리자: restricted 근거를 포함한 답변.
- 직원: 내용 노출 없이 hidden match 또는 권한 제한 안내.

## Task 6: 완료 기준

**Files:** 없음

- [ ] Calendar 일정 20개 이상 생성.
- [ ] 모든 Calendar 일정은 `paraworks-mng` 캘린더에 생성.
- [ ] Gmail 스레드 5개 이상, 총 메일 12개 이상 발송.
- [ ] Gmail To/CC/BCC와 Calendar 참석자에 `@paraworks.com` 주소가 0건.
- [ ] 한승헌, 김용희가 각각 Gmail/Calendar 근거에 5회 이상 등장.
- [ ] COO 김종우 일정이 2026-05-11부터 2026-05-22 사이 특히 바쁘게 보인다.
- [ ] Gmail/Calendar sync 결과가 ParaWorks에 반영된다.
- [ ] Review Queue에서 source evidence drawer로 원문 근거를 열 수 있다.
- [ ] 승인된 항목이 Projects/Timeline/RAG 답변에 반영된다.
- [ ] restricted 시나리오가 employee 계정에서 내용 노출 없이 동작한다.

## Self-Review

- Spec coverage: 사용자는 5월 한 달, 바쁜 COO, 한승헌/김용희 관련 Calendar 일정과 Gmail 발송 작업 계획을 요청했다. 본 계획은 기간, 인물, 일정, 메일 스레드, ParaWorks sync, Review/RAG 검증까지 포함한다.
- Placeholder scan: 실행자가 바로 만들 수 있도록 날짜, 시간, 제목, 참석자, 발송 순서, 검증 질문을 구체화했다.
- Contract safety: Calendar/Gmail 데이터는 `Source` 근거로 들어가고 Review Queue 승인 전 trusted knowledge로 취급하지 않는다. restricted 항목은 권한 필터 시연용으로 분리했다.
