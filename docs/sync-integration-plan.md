# Backend-Frontend Data Sync Resolution Plan

## 문제 분석 (Problem Analysis)

Slack, Gmail, Google Drive에서 데이터 수집(Sync)과 AI 비서 답변은 정상적으로 동작하나, 대시보드 및 프로젝트/검토/타임라인 화면에 반영되지 않는 문제를 확인했습니다.

### 원인 분석 (Root Causes)

1.  **AI 추출 연동 누락 (Missing Extraction Trigger)**:
    - 현재 데이터 수집(`Sync`) 후, 해당 데이터를 분석하여 리뷰 아이템(`ReviewItem`)을 만드는 AI 에이전트 분석 단계가 자동으로 실행되지 않고 있습니다.
    - 특히 Gmail과 Drive는 수집만 할 뿐, 분석을 거치지 않아 검토 대기열에 나타나지 않습니다.

2.  **검토 및 승인 프로세스 (Review & Approval)**:
    - 대시보드와 타임라인/기록/의사결정 화면은 사용자가 **승인(Approve)**한 데이터만 보여주도록 설계되어 있습니다.
    - 현재 리뷰 아이템 자체가 생성되지 않아 승인할 대상이 없으므로 해당 화면들이 비어 있는 상태입니다.

3.  **프로젝트 필터 제한 (Project Filter)**:
    - 프로젝트(Projects) 화면에서 Slack 데이터가 필터링되어 제외되어 있습니다.
    - 또한, Google Drive 데이터는 기본 권한이 `restricted`로 설정되어 있어, 일반 사용자(`employee`) 권한으로는 조회되지 않을 수 있습니다.

## 해결 계획 (Proposed Solutions)

### 1. 동기화 후 AI 분석 자동 트리거
- `sync_connector` API를 수정하여 Slack뿐만 아니라 Gmail, Drive 동기화가 완료된 후에도 즉시 **Company Memory Orchestration**을 실행하도록 개선합니다.
- 이를 통해 수집된 데이터가 즉시 리뷰 아이템 후보로 추출됩니다.

### 2. 프로젝트 뷰(Projects) 연동 확장
- 프로젝트 데이터 소스 타입에 `slack`을 추가하여, 슬랙 대화 내용도 프로젝트 맥락으로 묶여서 보이도록 수정합니다.

### 3. 대시보드 가시성 개선
- 대시보드에서 승인된 데이터뿐만 아니라 **검토 대기 중(pending_review)**인 항목도 함께 표시하여, 데이터 수집 후 진행 상황을 바로 확인할 수 있게 합니다.

## 세부 작업 항목 (Implementation Tasks)

- [ ] **API 연동**: `integrations.py`에서 동기화 성공 시 오케스트레이션 엔진 호출 로직 추가.
- [ ] **프로젝트 서비스**: `projects/service.py`에 Slack 소스 타입 추가.
- [ ] **대시보드 서비스**: `dashboard.py`에서 검토 대기 항목 카운트 및 최근 항목 포함.

## 확인 방법 (Verification)
1. Gmail/Drive 동기화 버튼 클릭.
2. 대시보드에서 "검토 대기" 숫자가 올라가는지 확인.
3. `/review` 페이지에서 추출된 후보들이 보이는지 확인.
4. 승인 버튼 클릭 후 `/timeline` 등에 정상 노출되는지 확인.
