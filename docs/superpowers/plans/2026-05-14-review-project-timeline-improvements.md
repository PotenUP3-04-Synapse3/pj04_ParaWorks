# Review, Project, Timeline 개선 작업계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slack 업무 후보 품질, 프로젝트 분류 정확도, Review 일괄 처리, 프로젝트 선택 UX, Timeline/Project 표시 정책, Review 렌더링 속도를 개선한다.

**Architecture:** Review Queue는 계속 신뢰 경계로 유지한다. Slack/Project 분류는 deterministic guard를 먼저 강화해 저품질 후보와 모호한 프로젝트 매칭을 줄이고, LLM 결과는 사용자가 Review에서 프로젝트를 직접 지정하거나 수정한 뒤 승인하도록 한다. Timeline 탭은 등록된 프로젝트만 보여주고, 승인된 Todo/History/Decision 데이터는 삭제하지 않고 RAG/Knowledge/Project 활동 영역에서 재사용한다.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js App Router, TypeScript, React, lucide-react.

---

## 현재 확인 사항

- `frontend/src/app/review/page.tsx`는 pending review 전체에 대해 `promotion-preview` API를 `Promise.all()`로 한 번에 호출한다. 검토사항이 200개 정도 쌓이면 렌더링과 네트워크 요청 수가 함께 늘어 느려질 가능성이 높다.
- 프로젝트 선택 UI는 Review 항목의 수정 모드 안에만 있다. 사용자가 검토 중 바로 “프로젝트 지정”만 하고 승인하기에는 흐름이 무겁다.
- `backend/app/api/v1/review.py`에는 단건 승인/반려와 agent 후보 승인 API만 있고, “현재 보이는 항목 전체 승인/반려” API가 없다.
- `frontend/src/app/timeline/page.tsx`는 `/api/v1/projects`의 `timeline_items`를 그대로 사용한다. 현재 `backend/app/knowledge/promotion.py`는 `history_event`, `todo`, `decision_record` 승인 시 보조 `TimelineEvent`도 생성하므로 같은 내용이 History/Todo와 Timeline mirror로 중복 표시될 수 있다.
- `backend/app/projects/service.py`는 DB에 등록된 프로젝트뿐 아니라 승인된 payload의 `project_key`와 approved knowledge의 `project_key`도 프로젝트 목록 후보로 삼는다. Timeline 탭에서는 등록 프로젝트만 표시해야 하므로 frontend 또는 backend에서 등록 프로젝트 기준 필터가 필요하다.
- `backend/app/projects/classifier.py`의 프로젝트 alias 매칭은 substring 중심이다. 예를 들어 “투자 유치” 프로젝트가 있을 때 “유치원 등교” 같은 일반 문장이 잘못 매칭될 수 있다.
- Slack 업무성 판단은 `backend/app/agents/slack_agent/service.py`, `backend/app/agents/slack_agent/llm.py`, `agent_slack/agent_slack.py`에 나뉘어 있다. 짧은 반응형 문장, 예의 문구, 내용 없는 요청 문구를 업무 후보로 올리지 않는 공통 품질 gate가 없다.

## 범위 결정

1차 작업에 포함:

- Slack 업무성 deterministic gate 추가
- 프로젝트 classifier 단어 경계/모호어 개선
- Timeline 탭 등록 프로젝트 필터와 중복 표시 제거
- Review 항목의 프로젝트 빠른 선택 UI
- Review 전체 승인/전체 반려 API와 UI
- Review 200개 렌더링 1차 개선: pagination과 lazy preview
- Project 탭 “승인된 활동” 설명 문구 개선
- 깨진 한글 copy를 touched file 안에서 교체

1차 작업 후 보류 판단:

- Review 페이지가 pagination/lazy preview 후에도 느리면 `react-window` 같은 가상 스크롤 도입을 별도 작업으로 분리한다.
- Slack LLM prompt 품질은 deterministic guard와 테스트 데이터로 먼저 막고, 실제 live LLM 프롬프트 대규모 개편은 golden dataset 결과를 보고 별도 작업으로 분리한다.

## 파일 구조

- Modify: `backend/app/agents/slack_agent/service.py`
  - evidence ranking/filter에 Slack 업무성 gate를 연결한다.
- Create: `backend/app/agents/slack_agent/quality.py`
  - 짧은 반응, 단독 예의 문구, 모호한 요청 문구를 걸러내는 deterministic 분류 함수를 둔다.
- Modify: `backend/app/agents/slack_agent/llm.py`
  - live LLM prompt에 “내용 없는 부탁/반응은 후보로 만들지 말라”는 요구사항과 project 선택 규칙을 추가한다.
- Modify: `agent_slack/agent_slack.py`
  - LangGraph Slack pipeline의 work filter prompt와 fallback 후보 생성을 보수적으로 정리한다.
- Modify: `backend/app/projects/classifier.py`
  - 한국어/영어 단어 경계, 모호어 stopword, alias hit scoring을 도입한다.
- Modify: `backend/app/projects/service.py`
  - Timeline용 item과 Project 활동용 item을 분리하고, registered project 기준 표시를 지원한다.
- Modify: `backend/app/api/v1/projects.py`
  - Timeline 탭에서 쓸 등록 프로젝트 전용 응답 또는 query flag를 지원한다.
- Modify: `backend/app/api/v1/review.py`
  - list pagination, lazy preview 대응, bulk approve/reject endpoint를 추가한다.
- Modify: `backend/app/schemas/review.py`
  - bulk action request schema를 추가한다.
- Modify: `backend/app/knowledge/promotion.py`
  - Todo/History 승인 결과가 Timeline 탭에서 중복으로 보이지 않도록 promotion result와 route 정책을 정리한다.
- Modify: `frontend/src/lib/api/types.ts`
  - Review pagination/bulk/project activity 타입을 추가한다.
- Modify: `frontend/src/app/review/page.tsx`
  - 프로젝트 빠른 선택 버튼, 전체 승인/반려 버튼, lazy preview, 더 보기 pagination을 추가한다.
- Modify: `frontend/src/app/timeline/page.tsx`
  - 등록 프로젝트만 표시하고 explicit timeline 항목만 보여준다.
- Modify: `frontend/src/app/projects/page.tsx`
  - “승인된 활동”의 의미와 장점을 UI 문구로 명시하고 중복 항목 표시를 줄인다.
- Test: `backend/tests/test_slack_agent_quality.py`
- Test: `backend/tests/test_project_memory_api.py`
- Test: `backend/tests/test_review.py`
- Test: `backend/tests/test_review_knowledge_promotion.py`
- Test: `backend/tests/test_slack_agent_api.py`
- Docs: `agent_slack/20260514_project_timeline_rag_progress.md`, `docs/portfolio-log.md`, `docs/superpowers/runbooks/session-handoff.md`

---

### Task 1: Slack 업무성 gate 추가

**Files:**
- Create: `backend/app/agents/slack_agent/quality.py`
- Modify: `backend/app/agents/slack_agent/service.py`
- Test: `backend/tests/test_slack_agent_quality.py`

- [ ] **Step 1: 실패 테스트를 추가한다**

`backend/tests/test_slack_agent_quality.py`를 만든다.

```python
from backend.app.agents.slack_agent.quality import classify_slack_work_signal


def test_polite_only_slack_messages_are_not_work_candidates() -> None:
    for text in ['후...', '부탁드립니다.', '확인 부탁드립니다.', '넵', '감사합니다', '좋아요']:
        signal = classify_slack_work_signal(text)
        assert signal.is_work_related is False
        assert signal.score < 0


def test_request_phrase_without_object_is_not_actionable() -> None:
    signal = classify_slack_work_signal('이번 주 안으로 부탁드립니다.')

    assert signal.is_work_related is False
    assert signal.reason == '업무 대상이 없는 짧은 요청 문구입니다.'


def test_actionable_slack_message_with_object_and_due_date_is_work() -> None:
    signal = classify_slack_work_signal('정산 자동화 화면 QA 결과를 금요일까지 공유 부탁드립니다.')

    assert signal.is_work_related is True
    assert signal.score >= 40
    assert '업무 대상' in signal.reason


def test_decision_message_is_work_even_without_due_date() -> None:
    signal = classify_slack_work_signal('Redis 큐는 이번 배치 작업의 기본 백엔드로 확정했습니다.')

    assert signal.is_work_related is True
    assert signal.score >= 50
```

- [ ] **Step 2: RED를 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_quality.py -q
```

Expected:

- FAIL: `ModuleNotFoundError: No module named 'backend.app.agents.slack_agent.quality'`

- [ ] **Step 3: 최소 구현을 추가한다**

`backend/app/agents/slack_agent/quality.py`를 만든다.

```python
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SlackWorkSignal:
    is_work_related: bool
    score: int
    reason: str


LOW_SIGNAL_EXACT = {
    '후',
    '후...',
    '넵',
    '네',
    '예',
    '감사합니다',
    '고맙습니다',
    '좋아요',
    '확인했습니다',
    '확인했습니다.',
}
LOW_SIGNAL_PHRASES = (
    '부탁드립니다',
    '확인 부탁드립니다',
    '확인 부탁드려요',
    '공유 부탁드립니다',
)
ACTION_TERMS = (
    '검토',
    '공유',
    '준비',
    '확인',
    '완료',
    '진행',
    '배포',
    '작성',
    '정리',
    '업데이트',
    '결정',
    '확정',
    'todo',
    'review',
    'confirm',
    'decide',
)
WORK_OBJECT_TERMS = (
    '프로젝트',
    '정산',
    '화면',
    '문서',
    '계약',
    '고객',
    '일정',
    'QA',
    '릴리즈',
    '배포',
    'Redis',
    '큐',
    'API',
    'RAG',
    'Slack',
    'Gmail',
    'Drive',
)
DUE_TERMS = ('오늘', '내일', '금요일', '이번 주', '까지', '마감', 'due')
DECISION_TERMS = ('결정', '확정', '합의', '채택', '보류', 'decided', 'agreed')


def classify_slack_work_signal(text: str) -> SlackWorkSignal:
    normalized = _normalize(text)
    if not normalized:
        return SlackWorkSignal(False, -30, '빈 메시지입니다.')

    lowered = normalized.lower()
    if lowered in {value.lower() for value in LOW_SIGNAL_EXACT}:
        return SlackWorkSignal(False, -40, '짧은 반응 메시지입니다.')

    has_action = _contains_any(normalized, ACTION_TERMS)
    has_object = _contains_any(normalized, WORK_OBJECT_TERMS) or _has_meaningful_noun_phrase(normalized)
    has_due = _contains_any(normalized, DUE_TERMS)
    has_decision = _contains_any(normalized, DECISION_TERMS)
    has_low_phrase = _contains_any(normalized, LOW_SIGNAL_PHRASES)

    if has_low_phrase and len(normalized) <= 24 and not has_object:
        return SlackWorkSignal(False, -25, '업무 대상이 없는 짧은 요청 문구입니다.')

    score = 0
    if has_decision:
        score += 55
    if has_action:
        score += 30
    if has_object:
        score += 25
    if has_due:
        score += 15
    if has_low_phrase and not has_object:
        score -= 20
    if len(normalized) < 12 and not has_decision:
        score -= 15

    if score >= 40:
        return SlackWorkSignal(True, score, '업무 대상과 행동 단서가 있습니다.')
    return SlackWorkSignal(False, score, '업무 후보로 보기에는 단서가 부족합니다.')


def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _has_meaningful_noun_phrase(text: str) -> bool:
    words = re.findall(r'[0-9A-Za-z가-힣]{2,}', text)
    generic = {'이번', '주로', '관련', '부탁', '확인', '공유'}
    return any(word not in generic for word in words)
```

- [ ] **Step 4: Slack evidence ranking에 연결한다**

`backend/app/agents/slack_agent/service.py`에서 `_evidence_importance_score()` 안에 gate를 연결한다.

```python
from backend.app.agents.slack_agent.quality import classify_slack_work_signal
```

```python
def _evidence_importance_score(chunk: DocumentChunk, source: Source) -> int:
    text = chunk.text.lower()
    metadata = source.raw_metadata or {}
    work_signal = classify_slack_work_signal(chunk.text)
    score = work_signal.score

    if not work_signal.is_work_related:
        score -= 30
    if any(keyword in text for keyword in _DECISION_KEYWORDS):
        score += 60
    if any(keyword in text for keyword in _ACTION_KEYWORDS):
        score += 35
    if any(keyword in text for keyword in _TECH_COST_KEYWORDS):
        score += 15
    if 40 <= len(chunk.text) <= 1200:
        score += 5
    if metadata.get('thread_ts') and metadata.get('thread_ts') != metadata.get('ts'):
        score += 5
    if metadata.get('reply_count'):
        score += min(int(metadata.get('reply_count') or 0), 5)
    if any(keyword in text for keyword in _LOW_SIGNAL_KEYWORDS) and len(chunk.text) < 80:
        score -= 20
    return score
```

- [ ] **Step 5: GREEN을 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent_api.py -q
uv run ruff check backend/app/agents/slack_agent/quality.py backend/app/agents/slack_agent/service.py backend/tests/test_slack_agent_quality.py
```

Expected:

- PASS

---

### Task 2: `agent_slack` LLM work filter prompt 보강

**Files:**
- Modify: `agent_slack/agent_slack.py`
- Test: `backend/tests/test_slack_agent_api.py`

- [ ] **Step 1: fake LLM 테스트에 저신호 메시지 케이스를 추가한다**

`backend/tests/test_slack_agent_api.py`에 `fake_process_daily_slack_sync` 입력이 실제 `changed_source_ids`만 받는지 보는 기존 테스트를 유지하고, 새 테스트를 추가한다.

```python
def test_agent_slack_sync_does_not_create_review_items_for_polite_only_messages(
    client,
    monkeypatch,
) -> None:
    from backend.app.core.config import Settings, get_settings
    from backend.app.core.demo_auth import DemoUser, get_demo_user
    from backend.app.connectors.base import SourceEvent
    from datetime import UTC, datetime

    class PoliteOnlyConnector:
        source_type = 'slack'

        def fetch_events(self):
            return [
                SourceEvent(
                    source_type='slack',
                    source_id='C123:1777600800.000100',
                    source_url='https://example.slack.com/archives/C123/p1777600800000100',
                    title='Slack polite only',
                    body='확인 부탁드립니다.',
                    author='U1',
                    participants=['U1'],
                    timestamp=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
                    permission_level='internal',
                    raw_metadata={'channel_id': 'C123', 'ts': '1777600800.000100'},
                )
            ]

    def override_settings() -> Settings:
        return Settings(paraworks_demo_mode=False, openai_api_key='openai-key')

    client.app.dependency_overrides[get_settings] = override_settings
    client.app.dependency_overrides[get_demo_user] = lambda: DemoUser(
        id='demo-admin',
        email='admin@paraworks.local',
        role='admin',
        permission_levels={'public', 'internal', 'restricted'},
        name='관리자',
        title='관리자',
        department='Platform',
    )
    monkeypatch.setattr(
        'backend.app.api.v1.integrations.get_sync_connector',
        lambda *args, **kwargs: PoliteOnlyConnector(),
    )
    monkeypatch.setattr(
        'backend.app.agents.slack_agent.sync_service.process_daily_slack_sync',
        lambda *args, **kwargs: {
            'model_name': 'gpt-4o-mini',
            'is_work_related': False,
            'run_cost': None,
            'candidates': [],
        },
    )

    response = client.post('/api/v1/integrations/slack/sync')

    assert response.status_code == 200
    assert response.json()['created_review_items'] == 0
```

- [ ] **Step 2: RED 또는 현 동작을 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_api.py::test_agent_slack_sync_does_not_create_review_items_for_polite_only_messages -q
```

Expected:

- 현재 fake 결과가 빈 candidates이면 PASS일 수 있다. PASS여도 이 테스트는 회귀 방지로 유지한다.

- [ ] **Step 3: `agent_slack/agent_slack.py` prompt를 보수적으로 수정한다**

`classify_work_node()`의 prompt에 다음 문장을 포함한다.

```python
prompt = (
    "다음 Slack 메시지 목록 중 회사 지식 후보로 검토할 가치가 있는 업무 메시지의 index만 콤마로 반환하세요. "
    "단독 반응, 예의 표현, 업무 대상이 없는 짧은 부탁 문구는 제외하세요. "
    "예: '후...', '넵', '부탁드립니다', '확인 부탁드립니다'만 있는 메시지는 NONE입니다. "
    "업무 후보는 구체적인 대상(프로젝트, 문서, 고객, 일정, 배포, 계약, 장애 등)과 행동/결정/기한 단서가 함께 있어야 합니다. "
    "업무 관련 내용이 전혀 없으면 NONE만 반환하세요.\n\n"
    f"{simple_list}"
)
```

- [ ] **Step 4: fallback 후보가 source 없는 ReviewCandidate를 만들지 않도록 막는다**

`extract_candidate_node()`의 fallback에서 `source_links=[]` 후보를 만들지 말고 빈 candidates를 반환한다.

```python
return {
    "candidates": [],
    "total_prompt_tokens": state.total_prompt_tokens + 100,
    "total_completion_tokens": state.total_completion_tokens + 100,
}
```

- [ ] **Step 5: 검증한다**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_api.py backend/tests/test_slack_agent.py -q
```

Expected:

- PASS

---

### Task 3: 프로젝트 분류 정확도 개선

**Files:**
- Modify: `backend/app/projects/classifier.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: “유치원 등교” 오분류 회귀 테스트를 추가한다**

`backend/tests/test_project_memory_api.py`에 추가한다.

```python
def test_project_classifier_does_not_match_ambiguous_substring(
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='project-investment-fundraising',
            name='투자 유치',
            summary='시드 투자 유치와 IR 미팅 준비',
        )
    )
    ingest_events(
        db_session,
        [
            _event(
                source_type='slack',
                source_id='slack-kindergarten',
                title='유치원 등교 일정',
                body='내일 유치원 등교 시간이 10분 늦춰졌습니다.',
                source_url='https://slack.mock/archives/C123/p1',
            ),
            _event(
                source_type='slack',
                source_id='slack-fundraising',
                title='투자 유치 IR 준비',
                body='투자 유치 프로젝트 IR 자료를 금요일까지 검토합니다.',
                source_url='https://slack.mock/archives/C123/p2',
            ),
        ],
    )

    candidates = build_project_assignment_candidates(db_session)

    assert [candidate.source_id for candidate in candidates] == ['slack-fundraising']
    assert candidates[0].project_key == 'project-investment-fundraising'
```

- [ ] **Step 2: RED를 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py::test_project_classifier_does_not_match_ambiguous_substring -q
```

Expected:

- 현재 substring 매칭이면 FAIL 가능성이 높다.

- [ ] **Step 3: alias 추출을 보수적으로 바꾼다**

`backend/app/projects/classifier.py`의 `_meaningful_terms()`와 `_contains_alias()`를 교체한다.

```python
AMBIGUOUS_PROJECT_TERMS = {
    '유치',
    '등교',
    '준비',
    '검토',
    '진행',
    '업무',
    '프로젝트',
    '관련',
    '확인',
}


def _meaningful_terms(text: str) -> list[str]:
    terms = re.findall(r'[0-9A-Za-z가-힣]{2,}', text)
    result: list[str] = []
    for term in terms:
        lowered = term.lower()
        if lowered in AMBIGUOUS_PROJECT_TERMS:
            continue
        if re.fullmatch(r'[가-힣]+', term) and len(term) < 3:
            continue
        result.append(term)
    return result


def _contains_alias(lowered_haystack: str, alias: str) -> bool:
    lowered_alias = alias.lower().strip()
    if not lowered_alias:
        return False
    if lowered_alias in {'ir', 'vc'}:
        return re.search(rf'(?<![0-9a-z]){re.escape(lowered_alias)}(?![0-9a-z])', lowered_haystack) is not None
    if re.search(r'[가-힣]', lowered_alias):
        pattern = rf'(?<![0-9A-Za-z가-힣]){re.escape(lowered_alias)}(?![0-9A-Za-z가-힣])'
        return re.search(pattern, lowered_haystack) is not None
    return lowered_alias in lowered_haystack
```

- [ ] **Step 4: 프로젝트 테스트를 검증한다**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py -q
uv run ruff check backend/app/projects/classifier.py backend/tests/test_project_memory_api.py
```

Expected:

- PASS

---

### Task 4: Timeline 탭을 등록 프로젝트와 명시적 Timeline 중심으로 정리

**Files:**
- Modify: `backend/app/projects/service.py`
- Modify: `backend/app/api/v1/projects.py`
- Modify: `frontend/src/app/timeline/page.tsx`
- Modify: `frontend/src/lib/api/types.ts`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: 등록되지 않은 프로젝트가 Timeline용 응답에 나오지 않는 테스트를 추가한다**

`backend/tests/test_project_memory_api.py`에 추가한다.

```python
def test_projects_api_registered_only_excludes_payload_only_projects(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='project-registered',
            name='등록 프로젝트',
            summary='사용자가 직접 등록한 프로젝트',
        )
    )
    db_session.add(
        TimelineEvent(
            project_key='project-unregistered',
            title='등록되지 않은 프로젝트 이벤트',
            result_summary='payload로만 생긴 프로젝트입니다.',
            source_links=['https://slack.mock/archives/C123/p1'],
            source_snippets=['등록되지 않은 프로젝트 이벤트'],
            confidence_score=0.8,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects?registered_only=true', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    assert [project['project_key'] for project in response.json()['projects']] == ['project-registered']
```

- [ ] **Step 2: History 승인으로 생기는 중복 표시 회귀 테스트를 추가한다**

```python
def test_project_timeline_items_do_not_duplicate_history_and_mirror_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        Project(
            project_key='project-alpha',
            name='Project Alpha',
            summary='Redis 의사결정 프로젝트',
        )
    )
    review_item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Redis 큐 운영 방향 공유',
            'summary': 'Redis 큐 운영 방향을 팀에 공유했습니다.',
            'project_key': 'project-alpha',
        },
        source_links=['https://slack.mock/archives/C123/p1'],
        source_snippets=['Redis 큐 운영 방향 공유 완료'],
        confidence_score=0.86,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(review_item)
    db_session.commit()
    db_session.refresh(review_item)

    approve_response = client.post(f'/api/v1/review/{review_item.id}/approve', headers={'X-Demo-User': 'demo-admin'})
    assert approve_response.status_code == 200

    response = client.get('/api/v1/projects?registered_only=true', headers={'X-Demo-User': 'demo-admin'})

    project = next(project for project in response.json()['projects'] if project['project_key'] == 'project-alpha')
    assert [item['item_type'] for item in project['timeline_items']] == ['timeline_event']
    assert len(project['timeline_items']) == 1
```

- [ ] **Step 3: RED를 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_registered_only_excludes_payload_only_projects backend/tests/test_project_memory_api.py::test_project_timeline_items_do_not_duplicate_history_and_mirror_timeline -q
```

Expected:

- 첫 테스트는 `registered_only` 미지원으로 FAIL.
- 두 번째 테스트는 history와 timeline mirror가 함께 보이면 FAIL.

- [ ] **Step 4: `build_project_memory()`에 registered_only 옵션을 추가한다**

`backend/app/projects/service.py`의 signature와 active key 계산을 바꾼다.

```python
def build_project_memory(db: Session, *, registered_only: bool = False) -> list[ProjectMemory]:
    ...
    active_project_keys = set(db_projects)
    if not registered_only:
        for item in all_approved_items:
            key = item.payload.get('project_key')
            if isinstance(key, str) and key:
                active_project_keys.add(key)
        for item in memory_records:
            if item.project_key:
                active_project_keys.add(item.project_key)
```

- [ ] **Step 5: timeline_items는 TimelineEvent만 포함하게 분리한다**

`_approved_memory_records()`는 Timeline 탭용으로는 `TimelineEvent`만 반환하게 하고, Project 탭 활동은 Task 8에서 별도 표시 문구로 정리한다. 최소 구현은 아래와 같다.

```python
def _approved_memory_records(db: Session, *, timeline_only: bool = False) -> list[ProjectTimelineItem]:
    records: list[ProjectTimelineItem] = []
    if not timeline_only:
        records.extend(_decision_records(db))
        records.extend(_history_records(db))
        records.extend(_todo_records(db))
    records.extend(_timeline_records(db))
    return _dedupe_timeline_records(records)
```

`build_project_memory()`에서는 timeline 탭/API의 `timeline_items`에 `timeline_only=True` 결과를 사용한다.

```python
memory_records = _approved_memory_records(db, timeline_only=True)
```

- [ ] **Step 6: API query flag를 연결한다**

`backend/app/api/v1/projects.py`의 `list_projects()`를 수정한다.

```python
@router.get('')
def list_projects(db: DbSession, user: CurrentUser, registered_only: bool = False) -> dict:
    projects = build_project_memory(db, registered_only=registered_only)
```

- [ ] **Step 7: Timeline 프론트는 등록 프로젝트 전용 API를 사용한다**

`frontend/src/app/timeline/page.tsx`에서 API 호출을 바꾼다.

```ts
apiGet<ProjectsResponse>("/api/v1/projects?registered_only=true")
```

그리고 timeline 표시 대상은 explicit timeline만 유지한다.

```ts
histories: project.timeline_items
  .filter((item) => item.review_status === "approved" && item.item_type === "timeline_event")
  .map(timelineHistoryFromProjectItem),
```

- [ ] **Step 8: 검증한다**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review_knowledge_promotion.py -q
cd frontend
npm.cmd exec tsc -- --noEmit
```

Expected:

- PASS

---

### Task 5: Review 항목에 프로젝트 빠른 선택 버튼 추가

**Files:**
- Modify: `frontend/src/app/review/page.tsx`
- Modify: `frontend/src/lib/api/types.ts`
- Verify: `backend/app/api/v1/review.py`

- [ ] **Step 1: 현재 프로젝트 선택이 수정 모드에만 있는지 확인한다**

Run:

```powershell
rg "소속 프로젝트|project_key|setEditProjectKey" frontend/src/app/review/page.tsx -n
```

Expected:

- `select`가 edit form 안에 있다.

- [ ] **Step 2: 빠른 선택 handler를 추가한다**

`frontend/src/app/review/page.tsx`에 추가한다.

```ts
async function updateItemProject(item: ReviewItem, projectKey: string) {
  const project = definedProjects.find((candidate) => candidate.project_key === projectKey);
  setPendingAction(`${item.id}:project`);
  setError(undefined);
  try {
    await apiPatch<ReviewItem>(`/api/v1/review/${item.id}`, {
      payload: {
        ...item.payload,
        project_key: projectKey,
        ...(project ? { project_name: project.name } : {}),
      },
    });
    await loadItems();
    notifyReviewQueueUpdated();
  } catch (caught) {
    setError(caught instanceof Error ? caught.message : "프로젝트를 저장하지 못했습니다.");
  } finally {
    setPendingAction(undefined);
  }
}
```

- [ ] **Step 3: 항목 카드 상단에 프로젝트 선택 버튼을 배치한다**

항목 action 영역 또는 title 아래에 select를 둔다.

```tsx
<label className="inline-flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-xs font-bold text-[var(--ink-muted)]">
  프로젝트
  <select
    value={stringField(item.payload.project_key) || "ad-hoc"}
    onChange={(event) => void updateItemProject(item, event.target.value)}
    disabled={Boolean(pendingAction)}
    className="bg-transparent text-xs font-bold text-ink outline-none"
  >
    <option value="ad-hoc">미분류</option>
    {definedProjects.map((project) => (
      <option key={project.project_key} value={project.project_key}>
        {project.name}
      </option>
    ))}
  </select>
</label>
```

- [ ] **Step 4: 검증한다**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- PASS

---

### Task 6: Review 전체 승인/전체 반려 API와 UI 추가

**Files:**
- Modify: `backend/app/schemas/review.py`
- Modify: `backend/app/api/v1/review.py`
- Modify: `frontend/src/app/review/page.tsx`
- Modify: `frontend/src/lib/api/types.ts`
- Test: `backend/tests/test_review.py`

- [ ] **Step 1: bulk approve/reject 테스트를 추가한다**

`backend/tests/test_review.py`에 추가한다.

```python
def test_bulk_review_action_approves_visible_pending_items(client, db_session) -> None:
    items = [
        ReviewItem(
            item_type='timeline_event',
            payload={'title': f'항목 {index}', 'result_summary': f'요약 {index}'},
            source_links=[f'https://slack.mock/{index}'],
            source_snippets=[f'근거 {index}'],
            confidence_score=0.8,
            permission_level='internal',
            status='pending_review',
        )
        for index in range(3)
    ]
    db_session.add_all(items)
    db_session.commit()

    response = client.post('/api/v1/review/bulk', json={'action': 'approve', 'scope': 'visible_pending'})

    assert response.status_code == 200
    assert response.json()['approved_count'] == 3
    assert response.json()['rejected_count'] == 0
    assert response.json()['skipped_count'] == 0
    assert db_session.query(TimelineEvent).count() == 3


def test_bulk_review_action_rejects_visible_pending_items_without_deleting_sources(client, db_session) -> None:
    item = ReviewItem(
        item_type='history_event',
        payload={'title': '반려 후보', 'summary': '반려해도 원본은 남아야 합니다.', 'source_ids': ['slack:1']},
        source_links=['https://slack.mock/1'],
        source_snippets=['원본 근거'],
        confidence_score=0.7,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(item)
    db_session.commit()

    response = client.post('/api/v1/review/bulk', json={'action': 'reject', 'scope': 'visible_pending'})

    assert response.status_code == 200
    assert response.json()['approved_count'] == 0
    assert response.json()['rejected_count'] == 1
    assert db_session.query(ReviewItem).filter_by(status='rejected').count() == 1
```

- [ ] **Step 2: RED를 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_review.py::test_bulk_review_action_approves_visible_pending_items backend/tests/test_review.py::test_bulk_review_action_rejects_visible_pending_items_without_deleting_sources -q
```

Expected:

- FAIL: `/api/v1/review/bulk`가 없다.

- [ ] **Step 3: request schema를 추가한다**

`backend/app/schemas/review.py`에 추가한다.

```python
from pydantic import BaseModel, Field


class ReviewBulkActionRequest(BaseModel):
    action: str = Field(pattern='^(approve|reject)$')
    scope: str = Field(default='selected', pattern='^(selected|visible_pending)$')
    item_ids: list[int] = Field(default_factory=list)
```

- [ ] **Step 4: bulk endpoint를 추가한다**

`backend/app/api/v1/review.py`에 추가한다.

```python
@router.post('/bulk')
def bulk_review_action(
    request: ReviewBulkActionRequest,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    if request.scope == 'visible_pending':
        candidates = db.scalars(
            select(ReviewItem).where(ReviewItem.status == 'pending_review').order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc())
        ).all()
        items = _visible_review_items(candidates, user, settings)
    else:
        items = [
            item
            for item in db.scalars(select(ReviewItem).where(ReviewItem.id.in_(request.item_ids))).all()
            if item.status == 'pending_review'
        ]
        items = _visible_review_items(items, user, settings)

    approved_ids: list[int] = []
    rejected_ids: list[int] = []
    skipped: list[dict[str, object]] = []
    for item in items:
        try:
            ensure_can_review_permission(user, item.permission_level)
            if request.action == 'approve':
                if not item.source_links or not item.source_snippets:
                    skipped.append({'id': item.id, 'reason': 'source_evidence_required'})
                    continue
                validate_review_item_for_approval(item)
                item.status = 'approved'
                item.reviewer_id = user.id
                item.reviewed_at = datetime.now(UTC)
                promote_review_item(db, item)
                approved_ids.append(item.id)
            else:
                item.status = 'rejected'
                item.reviewer_id = user.id
                item.reviewed_at = datetime.now(UTC)
                rejected_ids.append(item.id)
        except (HTTPException, ValueError) as exc:
            skipped.append({'id': item.id, 'reason': str(exc)})

    record_audit_log(
        db=db,
        actor=user,
        action=f'review.bulk_{request.action}',
        target_type='review_queue',
        target_id=request.scope,
        metadata={'approved_ids': approved_ids, 'rejected_ids': rejected_ids, 'skipped': skipped},
    )
    db.commit()
    return {
        'approved_count': len(approved_ids),
        'rejected_count': len(rejected_ids),
        'skipped_count': len(skipped),
        'approved_item_ids': approved_ids,
        'rejected_item_ids': rejected_ids,
        'skipped': skipped,
    }
```

- [ ] **Step 5: frontend 타입을 추가한다**

`frontend/src/lib/api/types.ts`에 추가한다.

```ts
export type ReviewBulkActionResponse = {
  approved_count: number;
  rejected_count: number;
  skipped_count: number;
  approved_item_ids: number[];
  rejected_item_ids: number[];
  skipped: Array<{ id: number; reason: string }>;
};
```

- [ ] **Step 6: Review 최상단에 전체 승인/반려 버튼을 추가한다**

`frontend/src/app/review/page.tsx`의 heading action 영역에 추가한다.

```tsx
<button
  type="button"
  onClick={() => void runBulkAction("approve")}
  disabled={Boolean(pendingAction) || groups.length === 0}
  className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
>
  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
  전체 승인
</button>
<button
  type="button"
  onClick={() => void runBulkAction("reject")}
  disabled={Boolean(pendingAction) || groups.length === 0}
  className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-3 text-sm font-semibold text-ink hover:bg-[var(--glass-strong)] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)]"
>
  <XCircle className="h-4 w-4" aria-hidden="true" />
  전체 반려
</button>
```

handler:

```ts
async function runBulkAction(action: "approve" | "reject") {
  const label = action === "approve" ? "승인" : "반려";
  if (!window.confirm(`현재 보이는 pending 검토사항을 모두 ${label}할까요?`)) return;
  setPendingAction(`bulk:${action}`);
  setError(undefined);
  try {
    const result = await apiPost<ReviewBulkActionResponse>("/api/v1/review/bulk", {
      action,
      scope: "visible_pending",
    });
    setPromotionNotice(undefined);
    setError(result.skipped_count ? `${result.skipped_count}개 항목은 처리하지 못했습니다.` : undefined);
    await loadItems();
    notifyReviewQueueUpdated();
  } catch (caught) {
    setError(caught instanceof Error ? caught.message : "일괄 처리에 실패했습니다.");
  } finally {
    setPendingAction(undefined);
  }
}
```

- [ ] **Step 7: 검증한다**

Run:

```powershell
uv run pytest backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q
cd frontend
npm.cmd exec tsc -- --noEmit
```

Expected:

- PASS

---

### Task 7: Review 200개 렌더링 1차 개선

**Files:**
- Modify: `backend/app/api/v1/review.py`
- Modify: `frontend/src/app/review/page.tsx`
- Modify: `frontend/src/lib/api/types.ts`
- Test: `backend/tests/test_review.py`

- [ ] **Step 1: pagination 테스트를 추가한다**

`backend/tests/test_review.py`에 추가한다.

```python
def test_list_review_items_supports_limit_offset(client, db_session) -> None:
    db_session.add_all(
        [
            ReviewItem(
                item_type='timeline_event',
                payload={'title': f'항목 {index}', 'result_summary': f'요약 {index}'},
                source_links=[f'https://slack.mock/{index}'],
                source_snippets=[f'근거 {index}'],
                confidence_score=0.8,
                permission_level='internal',
                status='pending_review',
            )
            for index in range(75)
        ]
    )
    db_session.commit()

    response = client.get('/api/v1/review?status=pending_review&limit=50&offset=0')

    assert response.status_code == 200
    body = response.json()
    assert len(body['items']) == 50
    assert body['total_count'] == 75
    assert body['limit'] == 50
    assert body['offset'] == 0
    assert body['has_more'] is True
```

- [ ] **Step 2: RED를 확인한다**

Run:

```powershell
uv run pytest backend/tests/test_review.py::test_list_review_items_supports_limit_offset -q
```

Expected:

- FAIL: `total_count`, `limit`, `offset`, `has_more`가 없다.

- [ ] **Step 3: review list API에 pagination을 추가한다**

`backend/app/api/v1/review.py`의 `list_review_items()` signature와 query를 바꾼다.

```python
def list_review_items(
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
    status: str = 'pending_review',
    limit: int = 50,
    offset: int = 0,
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    all_items = db.scalars(
        select(ReviewItem).where(ReviewItem.status == status).order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc())
    ).all()
    visible_all = _visible_review_items(all_items, user, settings)
    visible_items = visible_all[safe_offset:safe_offset + safe_limit]
```

응답에 추가한다.

```python
return {
    'groups': result_groups,
    'items': [_review_item_response(item, agent_runs.get(_agent_run_id(item) or -1)) for item in visible_items],
    'total_count': len(visible_all),
    'limit': safe_limit,
    'offset': safe_offset,
    'has_more': safe_offset + safe_limit < len(visible_all),
}
```

- [ ] **Step 4: frontend 타입을 갱신한다**

```ts
export type ReviewResponse = {
  groups: ReviewGroup[];
  items: ReviewItem[];
  total_count?: number;
  limit?: number;
  offset?: number;
  has_more?: boolean;
};
```

- [ ] **Step 5: Review page는 preview를 lazy load한다**

`loadItems()`에서 `promotion-preview` 전체 호출을 제거한다.

```ts
const review = await apiGet<ReviewResponse>(`/api/v1/review?status=pending_review&limit=${pageSize}&offset=${nextOffset}`);
setGroups(nextOffset === 0 ? review.groups || [] : [...groups, ...(review.groups || [])]);
setHasMore(Boolean(review.has_more));
setOffset((review.offset ?? 0) + (review.limit ?? pageSize));
```

항목이 펼쳐질 때 preview를 가져오는 함수를 추가한다.

```ts
async function ensurePreview(item: ReviewItem) {
  if (previews[item.id]) return;
  const preview = await apiGet<ReviewPromotionPreview>(`/api/v1/review/${item.id}/promotion-preview`);
  setPreviews((current) => ({ ...current, [item.id]: preview }));
}
```

그룹 toggle 시 호출한다.

```ts
function toggleGroup(group: ReviewGroup) {
  setExpandedGroups((prev) => ({ ...prev, [group.group_id]: !prev[group.group_id] }));
  for (const item of group.items) {
    void ensurePreview(item);
  }
}
```

- [ ] **Step 6: 더 보기 버튼을 추가한다**

```tsx
{hasMore ? (
  <button
    type="button"
    onClick={() => void loadItems(offset)}
    disabled={loading}
    className="mx-auto inline-flex h-10 items-center rounded-lg border border-[var(--line-soft)] bg-[var(--glass-elevated)] px-4 text-sm font-semibold text-ink"
  >
    더 보기
  </button>
) : null}
```

- [ ] **Step 7: 검증한다**

Run:

```powershell
uv run pytest backend/tests/test_review.py -q
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- PASS

---

### Task 8: Project 탭 “승인된 활동” 의미 명시

**Files:**
- Modify: `frontend/src/app/projects/page.tsx`
- Verify: `frontend/src/lib/api/types.ts`

- [ ] **Step 1: 현재 문구를 확인한다**

Run:

```powershell
rg "승인된 활동|timeline_items|활동" frontend/src/app/projects/page.tsx -n
```

Expected:

- “승인된 활동 타임라인” 영역의 설명이 부족하거나 깨진 문구가 있다.

- [ ] **Step 2: 섹션 제목과 설명을 교체한다**

프로젝트 상세 오른쪽/하단의 `timeline_items` 섹션 제목을 아래 문구로 교체한다.

```tsx
<div className="flex items-start justify-between gap-3">
  <div>
    <h3 className="text-base font-extrabold text-ink">승인된 프로젝트 활동</h3>
    <p className="mt-1 text-xs leading-5 text-muted">
      Review에서 승인된 결정, 히스토리, 타임라인, 할 일을 프로젝트별로 모은 기록입니다.
      원본 근거와 함께 남기 때문에 나중에 일정 변화, 결정 이유, 후속 할 일을 한곳에서 추적할 수 있습니다.
    </p>
  </div>
</div>
```

빈 상태 문구:

```tsx
<EmptyState text="아직 승인된 프로젝트 활동이 없습니다. Review에서 프로젝트를 지정하고 승인하면 결정, 히스토리, 타임라인, 할 일이 이곳에 쌓입니다." />
```

- [ ] **Step 3: item type label을 한국어로 정리한다**

```ts
const activityTypeLabels: Record<string, string> = {
  decision_record: "결정",
  history_event: "히스토리",
  timeline_event: "타임라인",
  todo: "할 일",
};
```

- [ ] **Step 4: 검증한다**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- PASS

---

### Task 9: 깨진 한글 copy 정리

**Files:**
- Modify: `frontend/src/app/review/page.tsx`
- Modify: `frontend/src/app/timeline/page.tsx`
- Modify: `backend/app/projects/service.py`
- Modify: `backend/app/projects/classifier.py`
- Modify: `backend/app/knowledge/promotion.py`
- Test: existing targeted tests

- [ ] **Step 1: touched file의 mojibake를 검색한다**

Run:

```powershell
rg "\\?꾩|\\?뱀|媛|揶|袁|諭|椰|寃|湲고" frontend/src/app/review/page.tsx frontend/src/app/timeline/page.tsx backend/app/projects/service.py backend/app/projects/classifier.py backend/app/knowledge/promotion.py -n
```

Expected:

- 깨진 문자열 위치가 출력된다.

- [ ] **Step 2: Review page 주요 copy를 한국어로 교체한다**

대표 교체 문구:

```ts
function itemSummary(item: ReviewItem) {
  const summary = stringField(item.payload[summaryKey(item)]);
  return summary || "요약이 생성되지 않았습니다. 근거를 확인한 뒤 수정하거나 추가 근거를 요청해 주세요.";
}
```

```ts
function routeLabel(route: string) {
  if (route === "/projects") return "프로젝트에서 보기";
  if (route === "/timeline") return "타임라인에서 보기";
  if (route === "/knowledge") return "지식 보관함에서 보기";
  return `${route} 열기`;
}
```

```ts
function itemTypeLabel(itemType: string) {
  const labels: Record<string, string> = {
    decision_record: "결정 기록",
    history_event: "히스토리",
    timeline_event: "타임라인",
    todo: "할 일",
    message_review: "메시지 검토",
    project_assignment: "프로젝트 연결",
  };
  return labels[itemType] ?? itemType.replaceAll("_", " ");
}
```

- [ ] **Step 3: Timeline page copy를 한국어로 교체한다**

대표 교체 문구:

```tsx
<h1>타임라인</h1>
<p>{loading ? "등록된 프로젝트 타임라인을 불러오고 있습니다." : error || "등록된 프로젝트에 승인된 타임라인 항목이 아직 없습니다."}</p>
```

```tsx
<p>등록한 프로젝트별로 승인된 타임라인 항목과 원본 근거를 확인합니다.</p>
```

- [ ] **Step 4: backend copy를 한국어로 교체한다**

`backend/app/knowledge/promotion.py`의 Todo timeline copy:

```python
timeline = TimelineEvent(
    title=f"[할 일] {normalized['title']}",
    result_summary=(
        f"담당자: {item.payload.get('assignee') or '미정'}, "
        f"기한: {item.payload.get('due_date') or '기한 없음'}"
    ),
    **base_fields,
)
```

- [ ] **Step 5: 재검색과 검증을 수행한다**

Run:

```powershell
rg "\\?꾩|\\?뱀|媛|揶|袁|諭|椰|寃|湲고" frontend/src/app/review/page.tsx frontend/src/app/timeline/page.tsx backend/app/projects/service.py backend/app/projects/classifier.py backend/app/knowledge/promotion.py -n
uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_slack_agent_quality.py -q
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- 검색 결과가 없거나, 의도적으로 남긴 테스트 fixture만 남는다.
- PASS

---

### Task 10: 최종 검증과 문서화

**Files:**
- Modify: `agent_slack/20260514_project_timeline_rag_progress.md`
- Modify: `docs/portfolio-log.md`
- Modify: `docs/superpowers/runbooks/session-handoff.md`

- [ ] **Step 1: 백엔드 targeted suite를 실행한다**

Run:

```powershell
uv run pytest backend/tests/test_slack_agent_quality.py backend/tests/test_slack_agent_api.py backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q
```

Expected:

- PASS

- [ ] **Step 2: ruff를 실행한다**

Run:

```powershell
uv run ruff check backend/app/agents/slack_agent backend/app/projects backend/app/api/v1/review.py backend/app/api/v1/projects.py backend/app/knowledge/promotion.py backend/tests/test_slack_agent_quality.py backend/tests/test_project_memory_api.py backend/tests/test_review.py
```

Expected:

- PASS

- [ ] **Step 3: frontend 검증을 실행한다**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- PASS

- [ ] **Step 4: 로컬 서버 smoke를 확인한다**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\paraworks-docker.ps1 -Stop
powershell -ExecutionPolicy Bypass -File .\scripts\paraworks-docker.ps1
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
Invoke-WebRequest -Uri http://127.0.0.1:3000/review -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:3000/timeline -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:3000/projects -UseBasicParsing
```

Expected:

- backend health `status=ok`
- `/review`, `/timeline`, `/projects` HTTP 200

- [ ] **Step 5: 문서를 업데이트한다**

`agent_slack/20260514_project_timeline_rag_progress.md`에 “작업 18 - Review/Project/Timeline 개선 구현”을 추가하고, 구현 결과와 검증 결과를 한국어로 기록한다.

`docs/portfolio-log.md`에는 다음 항목을 추가한다.

```markdown
## 2026-05-14 Review, Project, Timeline 품질 개선

- Slack 업무 후보 분류에서 짧은 반응, 단독 예의 문구, 업무 대상 없는 요청 문구를 제외하도록 deterministic gate를 추가했다.
- 프로젝트 분류에서 한국어 단어 경계와 모호어 처리를 강화해 substring 오분류를 줄였다.
- Review Queue에 프로젝트 빠른 선택과 전체 승인/반려를 추가하고, pagination/lazy preview로 다량 항목 렌더링 비용을 낮췄다.
- Timeline 탭은 등록 프로젝트와 승인된 timeline 항목 중심으로 정리하고, Project 탭은 승인된 활동의 의미를 명확히 안내한다.
- 검증: targeted backend tests, ruff, frontend TypeScript/build 통과.
```

`docs/superpowers/runbooks/session-handoff.md`에는 다음 작업자가 이어서 볼 수 있도록 변경 파일, 남은 리스크, 검증 명령을 기록한다.

- [ ] **Step 6: diff hygiene를 확인한다**

Run:

```powershell
git diff --check
git status --short
```

Expected:

- whitespace error 없음
- 변경 파일이 계획 범위 안에 있음

---

## 우선순위

1. Task 1, 3: Slack/Project 분류 품질을 먼저 고친다. 잘못된 후보가 적게 들어오면 이후 Review UX 부담이 줄어든다.
2. Task 4, 8: Timeline/Project 표시 정책을 정리한다. 사용자에게 “어디서 무엇을 봐야 하는지”가 먼저 명확해야 한다.
3. Task 5, 6: Review 사용성을 개선한다. 프로젝트 선택과 전체 승인/반려는 실제 운영 흐름을 줄여준다.
4. Task 7: 200개 성능 문제는 pagination/lazy preview로 1차 해결한다. 그래도 느리면 가상 스크롤 별도 작업으로 분리한다.
5. Task 9, 10: touched file copy 정리와 문서화를 마무리한다.

## 리스크와 보류 기준

- Review 전체 승인은 잘못된 대량 승인을 유발할 수 있으므로 `confirm()` 확인과 skipped count 표시를 반드시 넣는다.
- Bulk approve는 기존 단건 승인과 같은 `validate_review_item_for_approval()` 및 `promote_review_item()` 경로만 사용한다.
- Timeline에서 History/Todo를 숨겨도 DB 데이터는 삭제하지 않는다. `HistoryEvent`, `Todo`, `TimelineEvent`, RAG indexing 대상은 유지한다.
- Slack LLM live 호출은 테스트에서 절대 실행하지 않는다. 모든 테스트는 fake connector/fake LLM 또는 deterministic gate만 사용한다.
- 200개 렌더링이 pagination/lazy preview 후에도 느리면 `react-window` 도입을 별도 계획으로 분리한다.

## 자체 검토

- 요구사항 1은 Task 1, 2에서 처리한다.
- 요구사항 2는 Task 4에서 등록 프로젝트와 Timeline item 범위를 정리해 처리한다.
- 요구사항 3은 Task 5에서 처리한다.
- 요구사항 4는 Task 6에서 처리한다.
- 요구사항 5는 Task 7에서 1차 개선하고, 필요 시 별도 보류 기준을 둔다.
- 요구사항 6은 Task 4에서 Timeline item 중복 원인을 차단한다.
- 요구사항 7은 Task 3에서 처리한다.
- 요구사항 8은 Task 8에서 처리한다.
