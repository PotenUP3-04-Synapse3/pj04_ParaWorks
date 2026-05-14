# 슬랙 데이터 RAG 고도화 가이드 (Phase 1 & 2 구현 상세)

이 문서는 ParaWorks의 AI 비서가 슬랙 데이터를 더 똑똑하게 활용할 수 있도록 구축된 **메타데이터 태그 시스템**에 대한 설명서입니다. AI 비서 담당자가 이 데이터를 어떻게 활용하고 화면에 보여줄 수 있는지 상세히 안내합니다.

---

## 1. RAG란 무엇인가요? (쉽게 풀이)

**RAG(Retrieval-Augmented Generation)**는 AI가 답변을 할 때 단순히 자신이 아는 지식으로만 답하는 것이 아니라, **"우리 회사의 문서나 슬랙 대화록을 먼저 찾아보고(Retrieval), 그 내용을 참고해서 답변(Augmentation)하는 방식"**을 말합니다.

하지만 단순히 텍스트만 찾아오면 다음과 같은 문제가 생깁니다.
*   "이 말 누가 했지?" (작성자 불명)
*   "이게 어느 채널에서 나온 대화지?" (맥락 부족)
*   "이거 작년 이야기 아냐?" (시점 불분명)

이를 해결하기 위해 우리는 슬랙 데이터에 **'이름표(태그)'**를 붙이는 작업을 수행했습니다.

---

## 2. Phase 1 & 2 구현 내용 (어떻게 구성했나)

우리는 데이터를 수집하는 시점(Phase 1)과 AI가 분석하는 시점(Phase 2)으로 나누어 태그를 보강했습니다.

### Phase 1: 수집 시점의 '정적 태그' (Static Tags)
슬랙 API를 통해 메시지를 긁어올 때 즉시 붙는 기본 정보입니다.
*   **구현 위치**: `backend/app/connectors/slack.py`
*   **주요 태그**:
    *   `channel_name`: `#일반`, `#프로젝트-A` 같은 실제 채널 이름
    *   `author_name`: `U12345` 같은 ID가 아닌 `김철수` 같은 실제 이름
    *   `is_thread_reply`: 이것이 댓글인지 원문인지 구분
    *   `created_at_date`: `2024-05-13` 형태의 날짜
    *   `content_signature`: 똑같은 메시지가 여러 번 저장되지 않게 하는 고유 지문

### Phase 2: 분석 시점의 '동적 태그' (Dynamic Tags)
슬랙 에이전트(AI)가 대화 내용을 읽고 판단해서 붙여주는 지능형 정보입니다.
*   **구현 위치**: `backend/app/agents/slack_agent/service.py` (`back_propagate_slack_tags` 함수)
*   **주요 태그**:
    *   `category`: `Project`(프로젝트), `Operations`(운영), `Admin`(관리) 중 하나로 분류
    *   `topic_tag`: 대화의 핵심 주제 (예: "로그인 오류 수정", "연봉 협상")
    *   `importance`: 중요도 (`Low`, `Medium`, `High`)
*   **역전파(Back-propagation) 기술**: AI가 분석을 마친 후, 분석 결과(ReviewCandidate)에 담긴 태그 정보를 원본 데이터(`DocumentChunk`)에 다시 거꾸로 찾아가서 업데이트해주는 로직을 구현했습니다.

---

## 3. AI 비서 담당자를 위한 활용 가이드

AI 비서 담당자는 검색 결과(Search Results)에서 다음과 같은 메타데이터를 꺼내 쓸 수 있습니다.

### A. 답변 하단에 근거(Citation) 표시하기
AI가 답변을 생성한 후, 답변의 신뢰도를 높이기 위해 다음과 같은 포맷으로 출처를 노출하세요.

*   **추천 UI 포맷**: `[근거: {channel_name}, {author_name}, {created_at_date}]`
*   **예시**: "이번 벡터 DB는 pgvector를 사용하기로 결정되었습니다. **[근거: #pjt-ai-memory, 김철수, 2024-05-08]**"

### B. 특정 프로젝트/분류로 필터링하기
사용자가 "우리 **인사정책** 관련해서 슬랙에서 나온 이야기만 알려줘"라고 물으면, 검색 시 `topic_tag`나 `category` 필터를 사용할 수 있습니다.

*   **데이터 접근**: 검색 결과의 `metadata` 객체 안에 있는 `category`와 `topic_tag` 값을 사용하세요.
*   **중요도 활용**: `importance`가 `High`인 데이터에 검색 가중치를 더 주거나, 강조 표시를 할 수 있습니다.

### C. 검색 시 주의사항 (보안 정책)
*   **승인된 데이터만 검색**: 현재 시스템은 사용자가 '승인(Approve)' 버튼을 누른 슬랙 메시지만 벡터 DB(`pgvector`)에 들어갑니다. 따라서 답변에 쓰이는 데이터는 모두 사람이 검증한 고품질 데이터임이 보장됩니다.
*   **권한 필터**: 검색 결과의 `permission_level`을 확인하여, 질문한 사용자가 볼 권한이 있는 데이터만 답변에 포함하세요.

---

## 4. 데이터 구조 예시 (개발용)

검색 엔진(`pgvector`)에서 반환되는 데이터의 `metadata` 구조는 다음과 같습니다.

```json
{
  "chunk_id": 1024,
  "source_type": "slack",
  "channel_name": "#pjt-ai-memory",
  "author_name": "김철수",
  "created_at_date": "2024-05-13",
  "category": "Project",
  "topic_tag": "RAG 고도화",
  "importance": "High",
  "source_url": "https://company.slack.com/archives/C123/p1715000000000100"
}
```

이 정보를 바탕으로 사용자에게 "누가, 언제, 어디서" 말했는지를 정확하게 전달하는 똑똑한 AI 비서를 만들어주세요!
