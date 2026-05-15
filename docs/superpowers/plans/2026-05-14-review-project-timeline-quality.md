# Review/Project/Timeline 품질 개선 구현 계획

> **For agentic workers:** 이 계획을 실행할 때는 `superpowers:executing-plans`를 먼저 사용하고, 각 단계는 실패 테스트를 먼저 추가한 뒤 구현한다. 기존 사용자/동료 변경은 되돌리지 않는다.

**목표:** Slack/Gmail/Drive 동기화로 생성된 검토 항목을 실제 업무 단위와 등록된 프로젝트 중심으로 정리하고, 승인 후에는 검토 큐에서 사라지되 근거와 승인 지식은 RAG 및 프로젝트/타임라인 화면에서 재사용되도록 만든다.

**아키텍처:** 수집 데이터는 `Source`/`DocumentChunk`로 보존하고, 에이전트 출력은 `ReviewItem(status="pending_review")`에 머문다. 사용자가 승인하면 `DecisionRecord`, `HistoryEvent`, `Todo`, `TimelineEvent` 등 승인 지식으로 승격한다. 프로젝트/타임라인 화면은 승인 지식을 읽되, 프로젝트 탭은 등록된 프로젝트만 노출하고 중복으로 보이는 mirror record를 분리한다.

**기술 스택:** FastAPI, SQLAlchemy, Alembic, pytest, React/Next.js, TypeScript, Tailwind, existing deterministic/fake LLM test clients.

---

## 현재 확인된 상태

1. `backend/app/api/v1/review.py`는 pending review 전체를 한 번에 반환하고, bulk approve/reject API가 없다.
2. `frontend/src/app/review/page.tsx`는 Review 목록 로딩 시 모든 항목에 대해 promotion preview를 즉시 병렬 호출한다. 200개 항목에서는 이 부분이 렌더링/네트워크 병목이 될 가능성이 높다.
3. Review 카드에는 편집 모드 안에만 프로젝트 select가 있고, 사용자가 승인 직전에 프로젝트를 빠르게 지정하는 흐름이 약하다.
4. `backend/app/projects/service.py`의 `build_project_memory()`는 DB에 등록된 프로젝트뿐 아니라 승인 지식에 남아 있는 project key도 탭 후보로 확장한다. 이 때문에 “타임라인 탭에는 등록한 프로젝트만 표시” 요구와 어긋난다.
5. `promote_review_item()`은 `history_event`, `todo`, `decision_record` 승인 시 원본 승인 지식과 별도 `TimelineEvent` mirror record를 함께 만든다. 프로젝트 서비스가 둘 다 노출하면 같은 근거가 2개처럼 보일 수 있다.
6. `backend/app/projects/classifier.py`는 substring/약한 term 매칭에 기대고 있어 “투자 유치” 프로젝트가 “유치원 등교” 같은 문장과 잘못 연결될 수 있다.
7. `backend/app/agents/slack_agent/service.py`, `backend/app/agents/slack_agent/llm.py`, `agent_slack/agent_slack.py`는 짧은 의례 문구나 감탄사를 실제 업무 내용으로 보지 않도록 하는 강한 게이트가 부족하다.
8. 프로젝트 탭의 “승인된 활동 타임라인”은 사용자에게 어떤 데이터가 들어오고 왜 필요한지 설명이 부족하다.

---

## 작업 원칙

- 등록된 프로젝트 목록은 DB의 프로젝트 정의를 기준으로 한다. 승인 지식에 남아 있는 임시 project key는 탭을 새로 만들지 않는다.
- ReviewItem은 승인/반려 후 검토 목록에서 사라진다. 단, 승인된 지식과 원본 근거는 삭제하지 않고 RAG/프로젝트/기타 페이지에서 계속 참조한다.
- 프로젝트 분류는 LLM 추천과 사용자 확정을 분리한다. 애매한 항목은 “가장 가까운 프로젝트 후보”로 제안하되, 최종 연결은 사용자가 Review 화면에서 선택하거나 승인하면서 확정한다.
- 증거가 없는 항목은 승인 지식으로 승격하지 않는다.
- 성능 개선은 우선 pagination/lazy preview 같은 작은 변경으로 처리하고, virtualization까지 필요하면 별도 작업으로 보류한다.

---

## 단계별 구현 계획

### 1. 기준 테스트와 현재 실패 범위 고정

**목적:** 이후 변경이 기존 승인/RAG/프로젝트 흐름을 깨지 않는지 비교할 기준을 만든다.

**대상 파일**

- `backend/tests/test_project_memory_api.py`
- `backend/tests/test_review.py`
- `backend/tests/test_slack_agent.py`
- `backend/tests/test_slack_agent_api.py`
- `frontend/src/app/review/page.tsx`
- `frontend/src/app/timeline/page.tsx`
- `frontend/src/app/projects/page.tsx`

**작업**

1. 현재 관련 테스트를 실행하고 실패를 기록한다.
2. 기존 known failure와 이번 작업으로 고칠 failure를 분리한다.
3. `agent_slack/20260514_project_timeline_rag_progress.md`에 실행 결과와 다음 단계 상태를 계속 누적한다.

**검증 명령**

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_slack_agent.py backend/tests/test_slack_agent_api.py -q
```

---

### 2. Slack 업무 내용 판별 게이트 강화

**목적:** “후...”, “부탁드립니다.”, 단순 인사/반응/잡담처럼 앞뒤 맥락 없이는 업무로 볼 수 없는 메시지가 ReviewItem으로 넘어오지 않게 한다.

**신규/수정 파일**

- `backend/app/agents/slack_agent/quality.py` 신규
- `backend/app/agents/slack_agent/service.py`
- `backend/app/agents/slack_agent/llm.py`
- `agent_slack/agent_slack.py`
- `backend/tests/test_slack_agent_quality.py` 신규
- `backend/tests/test_slack_agent.py`

**실패 테스트 먼저 추가**

- `후...`는 업무 근거로 제외된다.
- `부탁드립니다.` 단독 문장은 업무 근거로 제외된다.
- `금요일까지 정산 파일 검토 부탁드립니다.`는 업무 대상, 행동, 기한 중 충분한 신호가 있어 포함된다.
- `확인했습니다`, `넵`, `감사합니다` 같은 단독 응답은 제외된다.
- 제외된 메시지는 agent run 비용/스킵 카운트에는 남길 수 있지만 `ReviewItem`으로 저장되지 않는다.

**구현 방향**

1. `SlackWorkSignal` 또는 유사한 작은 dataclass를 만든다.
2. 메시지를 다음 축으로 평가한다.
   - 업무 대상: 파일, 계약, 배포, 일정, 고객, 견적, 투자, IR, 장애, 정산 등
   - 업무 행동: 검토, 작성, 공유, 배포, 수정, 승인, 회신, 확인 요청 등
   - 실행 맥락: 담당자, 기한, 산출물, 링크, thread parent, channel project context
   - low-signal: 감탄사, 인사, 단독 요청 표현, 이모지/짧은 응답
3. “low-signal만 있고 업무 대상/행동이 없는 메시지”는 LLM 호출 전 deterministic 단계에서 제외한다.
4. LLM prompt에도 `no_work_object`, `low_context_request`, `personal_chatter` 같은 제외 이유를 명시한다.
5. `agent_slack/agent_slack.py`의 저비용 필터 프롬프트는 메시지 앞 50자만 보내는 방식에서, thread 주변 맥락과 channel/project context를 함께 제공하도록 개선한다.

---

### 3. 프로젝트 구분 로직의 substring 오탐 제거

**목적:** “유치”가 들어갔다고 “유치원 등교”를 투자 유치 프로젝트로 묶는 식의 부분 문자열 오탐을 막는다.

**수정 파일**

- `backend/app/projects/classifier.py`
- `backend/tests/test_project_memory_api.py`
- 필요 시 `backend/tests/test_projects_classifier.py` 신규

**실패 테스트 먼저 추가**

- 등록 프로젝트: `투자 유치`
- 입력: `유치원 등교 안내`
- 기대: 해당 프로젝트 후보로 분류하지 않음

- 등록 프로젝트: `투자 유치`
- 입력: `투자 유치 전략 회의 자료 공유`
- 기대: 해당 프로젝트 후보로 분류

**구현 방향**

1. 한글 token boundary를 고려한 phrase matching을 추가한다.
2. 프로젝트명/설명에서 1글자 또는 모호한 단어는 독립 매칭 term에서 제외한다.
3. 짧은 단어 하나만 맞는 경우 후보 점수를 크게 낮춘다.
4. 프로젝트명 전체 phrase 또는 의미 있는 term 2개 이상이 맞을 때만 강한 후보로 본다.
5. LLM이 추천한 프로젝트도 deterministic sanity check를 통과하지 못하면 “애매함”으로 표시하고 사용자 확인을 요구한다.

---

### 4. 타임라인 탭은 등록된 프로젝트만 표시

**목적:** 사용자가 프로젝트 탭에서 등록한 프로젝트만 타임라인 탭에 보이게 한다.

**수정 파일**

- `backend/app/projects/service.py`
- `backend/app/api/v1/projects.py`
- `backend/tests/test_project_memory_api.py`
- `frontend/src/app/timeline/page.tsx`
- `frontend/src/lib/api/types.ts`

**실패 테스트 먼저 추가**

- DB에 등록되지 않은 `project_key`가 승인 지식에 있어도 `/api/v1/projects`의 탭 후보로 노출되지 않는다.
- DB에 등록된 프로젝트는 아직 근거가 없어도 프로젝트 목록에는 표시된다.
- 타임라인 화면은 `/api/v1/projects/defined` 또는 등록 프로젝트 기준 응답만 사용한다.

**구현 방향**

1. `build_project_memory()`에서 탭/프로젝트 목록의 기준을 `Project` 테이블로 제한한다.
2. 승인 지식에 존재하지만 등록되지 않은 project key는 “미등록 승인 지식”으로만 내부 보존하고, UI 탭으로 만들지 않는다.
3. 공식 hard-coded 프로젝트가 아직 남아 있다면 제거하거나 seed data로 분리한다. 사용자가 등록하지 않은 프로젝트는 화면에 자동 표시하지 않는다.
4. 프론트 타임라인 탭은 registered project list를 기준으로 렌더링한다.

---

### 5. 승인 지식과 타임라인 표시 중복 정리

**목적:** 프로젝트 근거 자료/타임라인에서 같은 내용이 2개씩 보이는 문제를 제거한다.

**수정 파일**

- `backend/app/projects/service.py`
- `backend/app/knowledge/promotion.py`는 가능하면 유지하고, 표시 계층에서 분리
- `backend/tests/test_project_memory_api.py`
- `frontend/src/app/timeline/page.tsx`
- `frontend/src/app/projects/page.tsx`
- `frontend/src/lib/api/types.ts`

**실패 테스트 먼저 추가**

- `history_event` 승인 시 `HistoryEvent`와 mirror `TimelineEvent`가 생성되어도 프로젝트 API의 기본 활동 목록에는 같은 review/source 조합이 1번만 노출된다.
- 타임라인 탭은 `TimelineEvent` 성격의 항목만 보여주고, Todo/History 원본은 프로젝트 활동 또는 다른 페이지에서 사용할 수 있게 보존한다.

**구현 방향**

1. 백엔드 응답을 개념적으로 분리한다.
   - `timeline_items`: 시간순 타임라인에 표시할 항목
   - `activity_items`: 승인된 결정/히스토리/할 일/타임라인 후보를 모은 프로젝트 활동
   - `evidence_items`: connector 원본 근거
2. 같은 `review_item_id`, `source_id`, `title/summary hash`를 가진 mirror record는 표시 단계에서 dedupe한다.
3. 기존 RAG indexing은 승인 지식을 유지하되, 표시용 dedupe가 vector DB 원천 데이터를 삭제하지 않도록 한다.

---

### 6. Review 항목에서 프로젝트 선택을 빠르게 확정

**목적:** LLM이 애매하게 분류한 항목도 사용자가 검토 화면에서 등록 프로젝트 중 하나를 선택한 뒤 승인할 수 있게 한다.

**수정 파일**

- `frontend/src/app/review/page.tsx`
- `backend/app/api/v1/review.py`
- `backend/app/schemas/review.py`
- `backend/tests/test_review.py`

**실패 테스트 먼저 추가**

- `PATCH /api/v1/review/{item_id}`로 `payload.project_key`, `payload.project_name`을 변경할 수 있다.
- 등록 프로젝트가 아닌 key는 거절하거나 명확한 validation error를 반환한다.
- 프로젝트를 바꾼 뒤 승인하면 승인 지식의 project key가 사용자가 선택한 값으로 저장된다.

**구현 방향**

1. Review 카드 상단 또는 승인 버튼 근처에 “프로젝트 지정” control을 노출한다.
2. select 옵션은 현재 등록된 프로젝트만 사용한다.
3. LLM 추천 프로젝트는 badge로 표시하고, 사용자가 선택한 값이 있으면 사용자 선택을 우선한다.
4. 선택 즉시 저장하거나 승인 직전에 함께 PATCH 후 approve한다. UX는 “선택 즉시 저장”이 더 명확하다.

---

### 7. Review 탭 상단에 모두 승인/모두 반려 추가

**목적:** 검토 항목이 많을 때 사용자가 한 번에 처리할 수 있게 한다.

**수정 파일**

- `backend/app/api/v1/review.py`
- `backend/app/schemas/review.py`
- `backend/tests/test_review.py`
- `frontend/src/app/review/page.tsx`

**실패 테스트 먼저 추가**

- pending review 3개에 대해 bulk reject를 호출하면 모두 `rejected`가 되고 목록에서 사라진다.
- bulk approve는 승인 가능한 항목만 승인하고, evidence/필수 필드가 부족한 항목은 `skipped` 또는 `failed`로 보고한다.
- bulk API는 실제 원본 `Source`/승인 지식 데이터를 삭제하지 않는다.

**구현 방향**

1. `POST /api/v1/review/bulk` 추가
2. 요청 예시:

```json
{
  "action": "approve",
  "item_ids": [1, 2, 3]
}
```

3. 응답에는 `approved_count`, `rejected_count`, `failed_items`, `skipped_items`를 포함한다.
4. 프론트 상단에 “모두 승인”, “모두 반려” 버튼을 추가하고 확인 dialog를 둔다.
5. 필터/검색이 있는 경우 “현재 표시된 항목만”인지 “전체 pending”인지 버튼 문구에 명시한다. 첫 구현은 현재 로드된 항목 기준으로 제한한다.

---

### 8. Review 200개 렌더링 성능 개선

**목적:** 200개 검토 항목에서 초기 렌더링이 느린 원인을 줄인다.

**수정 파일**

- `backend/app/api/v1/review.py`
- `backend/app/schemas/review.py`
- `frontend/src/app/review/page.tsx`
- 필요 시 `frontend/src/lib/api/types.ts`

**실패/검증 시나리오**

- 200개 pending item fixture를 만들고 `/api/v1/review?limit=50&offset=0`이 50개만 반환하는지 확인한다.
- 프론트는 초기 로딩 시 promotion-preview를 모든 항목에 호출하지 않는다.

**구현 방향**

1. Review list API에 `limit`, `offset`, `include_previews=false`를 추가한다.
2. 프론트 초기 로딩은 preview 없이 50개만 가져온다.
3. promotion preview는 항목 expand 시 또는 “승인 영향 보기” 클릭 시 lazy load한다.
4. “더 보기” 버튼으로 다음 페이지를 불러온다.
5. 위 변경 후에도 체감이 나쁘면 list virtualization은 별도 작업으로 보류한다.

**보류 기준**

- pagination/lazy preview만으로 초기 렌더링이 충분히 개선되면 virtualization은 하지 않는다.
- DOM virtualization은 UI 구조 변경이 커질 수 있으므로 별도 계획서로 분리한다.

---

### 9. 프로젝트 탭 문구와 정보 구조 정리

**목적:** “승인된 활동 타임라인”에 어떤 내용이 들어가는지 사용자가 바로 이해하게 한다.

**수정 파일**

- `frontend/src/app/projects/page.tsx`
- 필요 시 `frontend/src/lib/api/types.ts`

**구현 방향**

1. 섹션명을 “승인된 프로젝트 활동”으로 바꾼다.
2. 안내 문구:

```text
Review에서 승인된 결정, 히스토리, 할 일, 타임라인 후보를 프로젝트별로 모은 기록입니다. 각 항목은 근거 링크와 함께 보존되며 RAG 검색, 회고, 진행 상황 파악에 사용됩니다.
```

3. 비어 있을 때:

```text
아직 승인된 활동이 없습니다. Review에서 이 프로젝트를 선택하고 승인하면 여기에 쌓입니다.
```

4. 실제로 타임라인 UI와 중복된다면 프로젝트 탭은 활동 요약/근거 중심, 타임라인 탭은 시간순 사건 중심으로 역할을 나눈다.

---

### 10. 문서화와 인수인계

**수정 파일**

- `agent_slack/20260514_project_timeline_rag_progress.md`
- `docs/portfolio-log.md`
- `docs/superpowers/runbooks/session-handoff.md`

**작업**

1. 각 구현 단계가 끝날 때마다 `agent_slack/20260514_project_timeline_rag_progress.md`에 한국어로 결과를 누적한다.
2. 사용자에게 보이는 제품 흐름이 바뀌면 `docs/portfolio-log.md`에 반영한다.
3. 다음 작업자가 이어받아야 할 known issue, 테스트 결과, 남은 의사결정은 `session-handoff.md`에 남긴다.

---

## 권장 작업 순서

1. Slack 업무 내용 게이트와 프로젝트 substring 오탐 테스트를 먼저 고정한다.
2. 등록 프로젝트만 노출하도록 백엔드 프로젝트 응답을 정리한다.
3. 승인 지식 표시 중복을 `timeline_items`/`activity_items` 분리로 정리한다.
4. Review 화면에 프로젝트 선택 control과 bulk approve/reject를 추가한다.
5. Review pagination/lazy preview로 200개 렌더링 병목을 완화한다.
6. 프로젝트 탭 문구와 빈 상태를 정리한다.
7. 문서와 handoff를 최신화한다.

---

## 최종 검증 계획

**백엔드**

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_slack_agent_api.py -q
```

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run ruff check backend/app/agents/slack_agent backend/app/projects backend/app/api/v1/review.py backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py backend/tests/test_review.py
```

**프론트엔드**

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

**수동 smoke**

1. 프로젝트 탭에서 새 프로젝트를 등록한다.
2. Slack 동기화를 실행한다.
3. Review 탭에서 프로젝트 추천/선택이 보이는지 확인한다.
4. 애매한 항목은 사용자가 프로젝트를 바꾼 뒤 승인한다.
5. 승인 항목이 Review 목록에서 사라지는지 확인한다.
6. 타임라인 탭에는 등록 프로젝트만 보이는지 확인한다.
7. 프로젝트 탭에는 승인된 프로젝트 활동이 중복 없이 보이는지 확인한다.
8. RAG/indexing 테스트에서 승인 지식과 source evidence가 유지되는지 확인한다.

---

## 완료 기준

- 저신호 Slack 메시지는 ReviewItem으로 생성되지 않는다.
- “유치원” 같은 부분 문자열 오탐이 프로젝트 분류를 만들지 않는다.
- 타임라인 탭은 등록된 프로젝트만 표시한다.
- Review에서 프로젝트를 사용자가 선택할 수 있고, 선택값이 승인 지식에 반영된다.
- Review 상단에서 현재 로드된 항목을 모두 승인/반려할 수 있다.
- 200개 pending review 초기 화면에서 모든 promotion preview를 즉시 호출하지 않는다.
- 프로젝트 근거/활동 목록에서 동일 근거가 2개씩 보이는 문제가 해결된다.
- 프로젝트 탭의 승인 활동 섹션이 사용자에게 목적과 장점을 설명한다.
- 모든 변경 결과와 검증 로그가 한국어 문서로 남아 있다.
