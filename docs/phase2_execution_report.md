# Phase 2: AI 자동 분류 및 사용자 검토 UI 실행 보고서

본 문서는 **프로젝트 중심 지식 자동화 계획서**의 두 번째 단계인 'AI 자동 분류 및 사용자 검토 UI' 기능 구현 및 검증 결과를 기록합니다.

---

## 1. 작업 내용 (Action)

### 1.1 AI 자동 분류 (프로젝트 매핑 로직) 구현
*   **변경 파일**: `backend/app/agents/slack_agent/service.py`
*   **작업 내용**:
    *   AI가 슬랙 대화를 분석하여 생성한 `topic_tag`를 바탕으로 사전에 정의된 프로젝트 키워드(`CANONICAL_PROJECTS`의 aliases)와 매칭하는 `_determine_project_from_tag` 헬퍼 함수를 추가했습니다.
    *   매칭된 프로젝트가 있다면 해당 `project_key`를, 적합한 프로젝트가 없다면 신규 프로젝트 여부를 알리는 `is_new_project` 플래그를 `ReviewItem`의 `payload`에 추가했습니다.
*   **가치**: 이제 슬랙 데이터가 수집될 때부터 어떤 프로젝트의 내용인지 시스템이 스스로 판단하여 제안할 수 있게 되었습니다.

### 1.2 리뷰 검토 API (수동 수정 기능) 보완
*   **변경 파일**: `backend/app/api/v1/review.py`
*   **작업 내용**:
    *   기존에는 `PATCH /api/v1/review/{item_id}` 호출 시 JSON 필드인 `payload` 전체를 덮어쓰는(Overwrite) 문제가 있었습니다.
    *   프론트엔드에서 사용자가 `project_key`만 수정해서 보낼 때 기존 `payload`의 다른 정보(category, importance 등)가 유실되지 않도록 **깊은 병합(Deep Merge)** 로직을 추가했습니다.
*   **가치**: 관리자가 AI의 추천이 틀렸다고 판단했을 때, 정보 유실 걱정 없이 안전하게 다른 프로젝트로 변경하여 승인할 수 있는 백엔드 기반을 완성했습니다.

---

## 2. 시행착오 및 해결 과정 (Mistakes & Troubleshooting)

*   **API Payload 유실 위험 발견**:
    *   **상황**: 리뷰 항목 수정 로직 검토 중 `setattr(item, field, value)` 방식으로 `payload` 전체가 치환되고 있음을 발견.
    *   **원인**: Pydantic의 `model_dump()`가 반환한 사전(Dict)을 그대로 SQLAlchemy 모델에 대입하면, JSON 필드 내부의 특정 키만 업데이트하는 것이 불가능함.
    *   **해결**: 업데이트되는 키가 `payload`일 경우, `dict(item.payload or {})`를 복사한 후 `update(value)`를 호출하여 부분 수정(Patch)이 가능하도록 선제적으로 방어 코드를 작성함.

---

## 3. 검증 결과 (Validation)

구현한 로직이 기존 시스템 및 새로 정의된 정책 위에서 정상 작동하는지 자동화 테스트를 통해 검증했습니다.

*   **실행 명령어**: `uv run pytest backend/tests/test_review.py backend/tests/test_slack_agent.py -v`
*   **테스트 결과**: 21개 항목 모두 통과 (100% Passed)
    *   리뷰 항목 수정 API (`test_patch_review_item_updates_payload`): 정상 (부분 패치 성공)
    *   리뷰 반려 및 승인 상태 변경 검증: 정상
    *   슬랙 에이전트 동작 및 프롬프트 생성 검증: 정상

---
**진행 상태**: Phase 2 완료. 이제 다음 단계인 'Phase 3: 승인 및 승격(Promotion) 파이프라인 완성'으로 넘어가겠습니다.
