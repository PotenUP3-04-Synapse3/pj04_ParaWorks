# 슬랙 에이전트 프론트엔드 및 DB 연동 작업 계획서

본 문서는 슬랙 에이전트(`agent_slack.py`)가 추출한 구조화된 데이터를 실제 서비스 화면에 연동하고, PostgreSQL DB에 영구 저장하기 위한 상세 계획을 정의합니다.

---

## 1. 데이터 매핑 및 DB 저장 계획

추출된 `ReviewCandidate` 데이터를 ParaWorks 표준 모델인 `ReviewItem` 테이블에 먼저 저장한 후, 승인 시 각 지식 테이블(`todos`, `decision_records` 등)로 프로모션합니다.

### 1.1 DB 테이블별 인서트 전략 (PostgreSQL)

| 대상 테이블 | 추출 데이터 필드 | 처리 방식 |
| :--- | :--- | :--- |
| **review_items** | 전체 추출 결과 (`JSON`) | 분석 직후 `pending_review` 상태로 저장. `payload` 필드에 JSON 전체 저장. |
| **todos** | `item_type == 'Todo'` | 리뷰 승인 시 인서트. `assignee`, `due_date`, `category` 포함. |
| **decision_records** | `item_type == 'Decision'` | 리뷰 승인 시 인서트. 결정 내용 및 배경 저장. |
| **history_events** | `item_type == 'Record'` | 리뷰 승인 시 인서트. 조직의 타임라인 기록으로 저장. |

### 1.2 상세 매핑 상세 (ReviewItem 기준)
*   **item_type**: `todo`, `decision`, `history_event` 등으로 변환 저장
*   **payload**:
    ```json
    {
      "title": "추출된 제목",
      "summary": "상세 요약 내용",
      "category": "Project | Operations | Administration | Ad-hoc",
      "topic_tag": "프로젝트명/서비스명",
      "assignee": "담당자 이름",
      "due_date": "YYYY-MM-DD",
      "source_channel": "채널명"
    }
    ```
*   **source_links**: 원문 슬랙 메시지 URL 리스트
*   **source_snippets**: 증거 문구 리스트

---

## 2. 프론트엔드 컴포넌트별 연동 계획

### 2.1 오늘의 업무 (Today's Tasks)
*   **연동 데이터**: `todos` 테이블 (또는 `review_items` 중 Todo 타입)
*   **필터링**: `due_date`가 오늘이거나 마감이 임박한 항목
*   **표시 항목**: `[category] title`, `assignee`, `due_date`

### 2.2 동기화 시간 (Sync Time)
*   **연동 데이터**: `sync_jobs` 테이블의 가장 최신 `completed_at`
*   **표시 항목**: "마지막 동기화: YYYY-MM-DD HH:MM:SS"

### 2.3 검토 사항 (Review Items)
*   **연동 데이터**: `review_items` 테이블
*   **필터링**: `status == 'pending_review'`, 최신순 3개
*   **이동 경로**: '전체 검토 보기' 클릭 시 `/review` 페이지로 이동

### 2.4 타임라인 (Activity Timeline)
*   **연동 데이터**: `sync_jobs` 및 `history_events`
*   **표시 항목**: "어떤 채널에서 몇 건의 지식을 추출했는지"에 대한 작업 로그 시각화

### 2.5 연동 관리 페이지 (Integration Management)
*   **기능**: 사용자가 '동기화(Sync)' 버튼 클릭 시 실제 슬랙 데이터 수집 및 에이전트 분석 트리거
*   **연동 API**: `POST /api/v1/integrations/slack/sync`
*   **워크플로우**:
    1.  슬랙 커넥터가 최신 메시지 수집 (`Source` 데이터 생성)
    2.  수집 완료 후 자동으로 `SlackAgent` 실행 (`process_daily_slack_sync`)
    3.  분석된 지식들을 `ReviewItem` 테이블에 인서트
    4.  프론트엔드에 실시간 상태 업데이트 (완료 시 대시보드 리로드)

---

## 3. 단계별 작업 프로세스

### Phase 1: 백엔드 API 및 트리거 연동 (API & Trigger Layer) - [완료: 2026-05-12]
1.  `backend/app/api/v1/integrations.py`의 `sync_connector` 로직 보완
2.  데이터 수집(`sync_connector_events`) 직후 `SlackAgent`를 호출하여 분석 파이프라인이 즉시 가동되도록 연결
3.  분석 결과를 `ReviewItem` 모델 객체로 변환하여 DB 인서트 로직 구현

### Phase 2: 프론트엔드 데이터 바인딩 (UI Layer) - [완료: 2026-05-12]
1.  `frontend/src/app/dashboard/page.tsx`에서 실제 `/api/v1/dashboard` 데이터 호출
2.  기존 Mockup UI를 `DashboardResponse` 타입에 맞춰 실제 데이터 렌더링으로 교체

### Phase 3: 사용자 토큰 및 정밀 동기화 (Advanced Sync) - [진행 중]
1.  사용자 토큰(User Token) 기반의 1:1 DM 수집 로직 통합.
2.  OAuth Flow 확장을 통한 사용자 권한 획득 UI/UX 구현.

---
**작성일자**: 2026-05-12
**작성자**: 김용희 (ParaWorks Dev Team)
