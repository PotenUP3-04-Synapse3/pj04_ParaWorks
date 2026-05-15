# Timeline/Project Evidence UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 타임라인은 실제 Slack 대화 시각 기준으로 날짜별 접기/펼치기와 title 중심 리스트를 제공하고, 프로젝트 탭은 승인된 활동의 원본 근거를 빠짐없이 보여준다.

**Architecture:** 백엔드 `ProjectsResponse`가 승인 시각이 아니라 source evidence의 실제 발생 시각(`occurred_at`)을 내려주도록 보강한다. 프론트 타임라인은 `occurred_at` 기준으로 날짜 그룹을 만들고, 기본 compact 모드에서는 title만 보여주며, expanded 모드에서 시간/source/status/요약을 보여준다. 프로젝트 탭의 `연결된 원본 근거`는 legacy `project_assignment`뿐 아니라 승인된 `decision_record/history_event/timeline_event/todo`의 source evidence에서도 생성한다.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, Next.js/React/TypeScript, Playwright.

---

## 현재 상태 요약

1. `frontend/src/app/timeline/page.tsx`
   - 리스트 카드가 `title`, `summary`, `History`를 모두 보여준다.
   - 상세 패널의 `Open source`는 이미 `target="_blank"`가 붙어 있으나, Slack history 버튼 클릭 후 새 탭 동작을 Playwright로 회귀 고정해야 한다.
   - 날짜 그룹은 `ProjectTimelineItem.created_at` 기준이다. 이 값은 Slack 대화 시간이 아니라 승인/knowledge row 생성 시간이다.
   - 날짜 그룹 접기/펼치기 UI가 없다.

2. `backend/app/projects/service.py`
   - `ProjectTimelineItem.created_at`은 `DecisionRecord/HistoryEvent/TimelineEvent/Todo.created_at`을 그대로 쓴다.
   - 실제 Slack timestamp는 `sources.raw_metadata.ts` 또는 Slack permalink URL에 남아 있지만 프로젝트 API로 전달되지 않는다.
   - `ProjectEvidence`는 `_evidence_from_assignments()`에서 `ReviewItem.item_type == 'project_assignment'` 승인 항목만 사용한다.
   - 최근 Slack Agent 흐름은 `project_assignment` 생성을 줄이고 approved knowledge에 `project_key`를 붙이므로, 승인된 내용이 많아도 `연결된 원본 근거`가 비어 보일 수 있다.

3. 테스트 충돌
   - `backend/tests/test_project_memory_api.py::test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence`는 이번 요구사항과 반대다.
   - 이 테스트는 “approved knowledge를 원본 근거로 표시하지 않는다”를 기대하므로, 이번 작업에서 “approved knowledge의 source evidence도 프로젝트 원본 근거로 표시한다”로 정책을 바꾸고 테스트를 교체한다.

---

## 파일 구조

- Modify: `backend/app/projects/service.py`
  - `ProjectTimelineItem`에 `occurred_at` 추가
  - source URL/source id 기반 실제 source 발생 시각 조회
  - approved knowledge source evidence를 `ProjectEvidence`로 변환
  - evidence/source type/count 계산을 approved activity 기반까지 포함

- Modify: `frontend/src/lib/api/types.ts`
  - `ProjectTimelineItem.occurred_at` 필드 추가

- Modify: `frontend/src/app/timeline/page.tsx`
  - 리스트 compact 모드에서는 title만 노출
  - 날짜 그룹 접기/펼치기 state 추가
  - `occurred_at` 기준 날짜/시간 렌더링
  - group별 `간단히 보기/자세히 보기` 또는 `최소화/최대화` 버튼 추가

- Modify: `frontend/src/app/projects/page.tsx`
  - 백엔드 evidence가 채워지는지 전제로 기존 원본 링크 UI 유지
  - 필요 시 evidence 빈 상태 문구를 “승인된 활동에 source link가 없을 때”로 구체화

- Modify: `backend/tests/test_project_memory_api.py`
  - approved knowledge source evidence 생성 테스트 추가/기존 충돌 테스트 수정
  - timeline item `occurred_at`이 Slack source timestamp 기준인지 검증

- Modify: `frontend/e2e/timeline-project-date-groups.spec.ts`
  - 리스트 compact 모드 title-only 검증
  - `occurred_at` 기준 날짜 그룹 검증
  - 날짜 그룹 최소화/최대화 검증
  - Slack history -> Open source 새 탭 속성 검증 유지

- Modify: `frontend/e2e/projects-source-links.spec.ts`
  - `evidence`가 approved activity source에서 내려오는 mock 응답을 기준으로 표시/링크 검증

- Update: `agent_slack/20260514_project_timeline_rag_progress.md`
  - 작업 완료 시 한글 기록 추가

- Update: `docs/portfolio-log.md`
  - 제품 흐름/검증 증거 변경 기록

---

## Task 1: Backend 프로젝트 타임라인 실제 발생 시각 추가

**Files:**
- Modify: `backend/app/projects/service.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: failing test 작성**

`backend/tests/test_project_memory_api.py`에 아래 테스트를 추가한다. Slack permalink의 `p1777600800000100`은 `1777600800.000100`으로 환원되어 `2026-05-01T10:00:00Z` 근처의 실제 대화 시각으로 정렬되어야 한다.

```python
from datetime import UTC, datetime

from backend.app.models import Project, Source, TimelineEvent


def test_project_timeline_items_use_slack_source_timestamp_for_occurred_at(client, db_session) -> None:
    project = Project(
        project_key='project-alpha',
        name='Project Alpha',
        summary='Slack source time test',
    )
    source = Source(
        source_type='slack',
        source_id='C123:1777600800.000100',
        source_url='https://example.slack.com/archives/C123/p1777600800000100',
        title='Slack 원문',
        author='김하나',
        permission_level='internal',
        raw_metadata={'ts': '1777600800.000100', 'channel_id': 'C123'},
    )
    timeline = TimelineEvent(
        project_key='project-alpha',
        title='실제 Slack 대화 기준 타임라인',
        result_summary='승인 시각이 아니라 Slack 대화 시각으로 보여야 합니다.',
        source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
        source_snippets=['Slack에서 오전에 논의했습니다.'],
        confidence_score=0.9,
        permission_level='internal',
        review_status='approved',
        created_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )
    db_session.add_all([project, source, timeline])
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    project_payload = next(project for project in response.json()['projects'] if project['project_key'] == 'project-alpha')
    item = project_payload['timeline_items'][0]
    assert item['created_at'] == '2026-05-15T09:00:00+00:00'
    assert item['occurred_at'].startswith('2026-05-01T10:00:00')
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py::test_project_timeline_items_use_slack_source_timestamp_for_occurred_at -q
```

Expected: `KeyError: 'occurred_at'` 또는 `occurred_at` 미존재로 실패한다.

- [ ] **Step 3: 최소 구현**

`backend/app/projects/service.py`의 dataclass와 생성 경로를 아래 의미로 수정한다.

```python
@dataclass(frozen=True)
class ProjectTimelineItem:
    id: str
    item_type: str
    title: str
    summary: str
    source_links: list[str]
    source_snippets: list[str]
    confidence_score: float
    permission_level: str
    review_status: str
    created_at: str
    occurred_at: str
    evidence_reason: str
    project_key: str | None = None
```

`_approved_memory_records(db)` 안에서 source lookup map을 먼저 만든다.

```python
def _source_lookup_by_url(db: Session) -> dict[str, Source]:
    sources = db.scalars(select(Source)).all()
    return {source.source_url: source for source in sources if source.source_url}
```

Slack source timestamp를 ISO 문자열로 변환하는 helper를 추가한다.

```python
from datetime import UTC, datetime
from backend.app.models import Source


def _occurred_at_from_source_links(
    source_links: list[str],
    source_by_url: dict[str, Source],
    fallback: datetime,
) -> str:
    for link in source_links:
        source = source_by_url.get(link)
        if source:
            raw_ts = (source.raw_metadata or {}).get('ts')
            if isinstance(raw_ts, str):
                try:
                    return datetime.fromtimestamp(float(raw_ts), tz=UTC).isoformat()
                except ValueError:
                    pass
            return source.created_at.isoformat()

        parsed_ts = _slack_ts_from_permalink(link)
        if parsed_ts:
            return datetime.fromtimestamp(parsed_ts, tz=UTC).isoformat()

    return fallback.isoformat()


def _slack_ts_from_permalink(link: str) -> float | None:
    if '/p' not in link:
        return None
    raw = link.rsplit('/p', 1)[-1].split('?', 1)[0]
    if len(raw) < 11 or not raw.isdigit():
        return None
    seconds = raw[:10]
    micros = raw[10:].ljust(6, '0')[:6]
    return float(f'{seconds}.{micros}')
```

각 `ProjectTimelineItem(...)` 생성 시 `occurred_at`을 넣는다.

```python
source_by_url = _source_lookup_by_url(db)

ProjectTimelineItem(
    id=f'timeline_event:{item.id}',
    item_type='timeline_event',
    title=item.title,
    summary=item.result_summary,
    source_links=item.source_links,
    source_snippets=item.source_snippets,
    confidence_score=item.confidence_score,
    permission_level=item.permission_level,
    review_status=item.review_status,
    created_at=item.created_at.isoformat(),
    occurred_at=_occurred_at_from_source_links(item.source_links, source_by_url, item.created_at),
    evidence_reason='승인된 타임라인 항목이 이 프로젝트와 연결되어 있습니다.',
    project_key=item.project_key,
)
```

- [ ] **Step 4: GREEN 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py::test_project_timeline_items_use_slack_source_timestamp_for_occurred_at -q
```

Expected: `1 passed`

---

## Task 2: Backend 프로젝트 원본 근거를 approved activity source에서 생성

**Files:**
- Modify: `backend/app/projects/service.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: failing test 작성**

기존 `test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence`는 삭제하거나 아래 테스트로 교체한다.

```python
from datetime import UTC, datetime

from backend.app.models import HistoryEvent, Project


def test_projects_api_builds_evidence_from_approved_project_activity_sources(client, db_session) -> None:
    project = Project(
        project_key='project-alpha',
        name='Project Alpha',
        summary='Approved activity evidence test',
    )
    history = HistoryEvent(
        project_key='project-alpha',
        title='Redis 큐 상태 확인',
        reason='Slack에서 Redis 큐 상태를 확인했습니다.',
        source_links=['https://example.slack.com/archives/C123/p1777600800000100'],
        source_snippets=['Redis 큐 상태 확인 완료'],
        confidence_score=0.91,
        permission_level='internal',
        review_status='approved',
        created_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )
    db_session.add_all([project, history])
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    project_payload = next(project for project in response.json()['projects'] if project['project_key'] == 'project-alpha')
    assert project_payload['evidence_count'] == 1
    assert project_payload['source_types'] == ['slack']
    assert project_payload['evidence'][0]['title'] == 'Redis 큐 상태 확인'
    assert project_payload['evidence'][0]['source_url'] == 'https://example.slack.com/archives/C123/p1777600800000100'
    assert project_payload['evidence'][0]['source_snippet'] == 'Redis 큐 상태 확인 완료'
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_builds_evidence_from_approved_project_activity_sources -q
```

Expected: `evidence_count == 0`으로 실패한다.

- [ ] **Step 3: 최소 구현**

`backend/app/projects/service.py`에 approved record 기반 evidence builder를 추가한다.

```python
def _evidence_from_activity_items(items: list[ProjectTimelineItem]) -> list[ProjectEvidence]:
    evidence: list[ProjectEvidence] = []
    seen: set[str] = set()
    for item in items:
        for index, link in enumerate(item.source_links):
            if not link.strip():
                continue
            identity = f'{item.project_key}:{link}'
            if identity in seen:
                continue
            seen.add(identity)
            evidence.append(
                ProjectEvidence(
                    id=identity,
                    source_id=link,
                    source_type=_source_type_from_link(link),
                    title=item.title,
                    source_url=link,
                    source_snippet=item.source_snippets[index] if index < len(item.source_snippets) else '',
                    permission_level=item.permission_level,
                    timestamp=item.occurred_at,
                    task_summary=item.summary,
                    evidence_reason=item.evidence_reason,
                )
            )
    return sorted(evidence, key=lambda item: (item.timestamp, item.id), reverse=True)


def _source_type_from_link(link: str) -> str:
    lowered = link.lower()
    if 'slack' in lowered:
        return 'slack'
    if 'mail.google' in lowered or 'gmail' in lowered:
        return 'gmail'
    if 'drive.google' in lowered or 'docs.google' in lowered:
        return 'drive'
    if 'calendar.google' in lowered or 'calendar' in lowered:
        return 'calendar'
    return 'source'
```

`build_project_memory()`에서 evidence를 합친다.

```python
assignment_evidence = _evidence_from_assignments(assignment_evidence_items)
linked_records = _memory_records_for_project(project_key, project_link_items, memory_records)
timeline_items = _timeline_items_from_records(linked_records)
activity_items = _dedupe_activity_items(linked_records)
evidence = _dedupe_project_evidence([*assignment_evidence, *_evidence_from_activity_items(activity_items)])
```

중복 제거 helper를 추가한다.

```python
def _dedupe_project_evidence(items: list[ProjectEvidence]) -> list[ProjectEvidence]:
    deduped: list[ProjectEvidence] = []
    seen: set[str] = set()
    for item in items:
        identity = f'{item.source_url}:{item.source_snippet}'
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(item)
    return sorted(deduped, key=lambda item: (item.timestamp, item.id), reverse=True)
```

- [ ] **Step 4: 관련 backend 테스트 실행**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py -q
```

Expected: 프로젝트 메모리 테스트가 모두 통과한다. 오래된 정책 테스트가 남아 실패하면 이 요구사항에 맞게 테스트명을 `test_projects_api_builds_evidence_from_approved_project_activity_sources`로 바꿨는지 확인한다.

---

## Task 3: Frontend 타입과 타임라인 title-only 리스트

**Files:**
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/timeline/page.tsx`
- Test: `frontend/e2e/timeline-project-date-groups.spec.ts`

- [ ] **Step 1: failing Playwright test 작성**

`frontend/e2e/timeline-project-date-groups.spec.ts`의 mock `timeline_items`에 `occurred_at`을 추가하고, 리스트가 title만 보여주는지 검증한다.

```ts
await expect(page.getByRole("heading", { name: "오전 점검" })).toBeVisible();
await expect(page.getByText("Redis 점검")).toBeHidden();
await expect(page.getByText("History: Redis 점검")).toBeHidden();
```

Mock item 예시:

```ts
{
  id: "timeline_event:1",
  item_type: "timeline_event",
  title: "오전 점검",
  summary: "Redis 점검",
  source_links: ["https://slack.example/1"],
  source_snippets: ["점검"],
  confidence_score: 0.9,
  permission_level: "internal",
  review_status: "approved",
  created_at: "2026-05-15T09:00:00Z",
  occurred_at: "2026-05-14T01:00:00Z",
  evidence_reason: "승인된 항목",
  project_key: "project-alpha",
}
```

- [ ] **Step 2: RED 확인**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts --project=chromium-desktop
```

Expected: 현재 리스트에 summary/history가 보여 실패한다.

- [ ] **Step 3: 타입 추가**

`frontend/src/lib/api/types.ts`의 `ProjectTimelineItem`에 `occurred_at`을 추가한다.

```ts
export type ProjectTimelineItem = {
  id: string;
  item_type: string;
  title: string;
  summary: string;
  source_links: string[];
  source_snippets: string[];
  confidence_score: number;
  permission_level: string;
  review_status: string;
  created_at: string;
  occurred_at?: string;
  evidence_reason: string;
  project_key?: string | null;
};
```

- [ ] **Step 4: title-only 렌더링**

`frontend/src/app/timeline/page.tsx`에서 리스트 카드의 summary/history 블록을 제거하고 title만 남긴다.

```tsx
<article key={item.id} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
  <div className="flex items-center justify-between gap-3">
    <h3 className="min-w-0 truncate text-[15px] font-extrabold text-ink">{item.title}</h3>
    <button
      type="button"
      aria-pressed={selectedHistoryId === item.id}
      className={`icon-button small ${selectedHistoryId === item.id ? "active" : ""}`}
      aria-label={`Open ${item.title}`}
      onClick={() => setSelectedHistoryId((current) => (current === item.id ? undefined : item.id))}
    >
      <FileClock className="h-4 w-4" aria-hidden="true" />
    </button>
  </div>
</article>
```

- [ ] **Step 5: Playwright GREEN 확인**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts --project=chromium-desktop
```

Expected: title-only 관련 assertion 통과. 날짜 그룹 관련 assertion은 Task 4 전까지 조정 중일 수 있다.

---

## Task 4: Timeline 날짜 그룹 최소화/최대화 및 occurred_at 기준 정렬

**Files:**
- Modify: `frontend/src/app/timeline/page.tsx`
- Test: `frontend/e2e/timeline-project-date-groups.spec.ts`

- [ ] **Step 1: failing Playwright test 작성**

`timeline-project-date-groups.spec.ts`에 아래 assertion을 추가한다.

```ts
await expect(page.getByText("2026년 5월 14일")).toBeVisible();
await expect(page.getByText("2026년 5월 15일")).toBeHidden();

await page.getByRole("button", { name: "날짜 전체 보기" }).click();
await expect(page.getByText("2026년 5월 15일")).toBeVisible();

await page.getByRole("button", { name: "2026년 5월 14일 자세히 보기" }).click();
await expect(page.getByText("01:00")).toBeVisible();
await expect(page.getByText("Slack")).toBeVisible();

await page.getByRole("button", { name: "2026년 5월 14일 간단히 보기" }).click();
await expect(page.getByText("01:00")).toBeHidden();
```

정책:

- 기본: 가장 최신 날짜 그룹만 표시한다.
- `날짜 전체 보기`: 모든 날짜 그룹을 표시한다.
- 날짜 그룹별 기본 상태: compact(title-only)
- 그룹별 `자세히 보기`: 해당 날짜 그룹 내부 항목에 시간/source/status를 표시한다.
- 그룹별 `간단히 보기`: 해당 날짜 그룹 내부 항목을 다시 title-only로 표시한다.

- [ ] **Step 2: RED 확인**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts --project=chromium-desktop
```

Expected: 버튼/표시 정책이 없어 실패한다.

- [ ] **Step 3: state 추가**

`TimelinePage`에 전체 날짜 표시 여부와 expanded group state를 추가한다.

```tsx
const [showAllDates, setShowAllDates] = useState(false);
const [expandedDateLabels, setExpandedDateLabels] = useState<Set<string>>(new Set());
```

프로젝트 변경 시 state 초기화:

```tsx
onClick={() => {
  setSelectedProjectId(project.id);
  setSelectedHistoryId(undefined);
  setShowAllDates(false);
  setExpandedDateLabels(new Set());
}}
```

- [ ] **Step 4: occurred_at 기준 변환/정렬**

`timelineHistoryFromProjectItem()`에서 `occurred_at`을 우선 사용한다.

```ts
const occurredAt = item.occurred_at || item.created_at;
return {
  id: item.id,
  createdAt: occurredAt,
  time: formatTime(occurredAt),
  source: sourceFromLinks(item.source_links),
  title: item.title,
  summary: item.summary,
  history: item.summary || "No approved timeline summary.",
  status: item.review_status === "approved" ? "approved" : "reviewing",
  sourceUrl: item.source_links[0] ?? "",
  snippets: item.source_snippets.map((snippet) => ({
    author: `${sourceFromLinks(item.source_links)} evidence · ${item.evidence_reason || "승인된 프로젝트 근거"}`,
    body: snippet,
    time: formatTime(occurredAt),
  })),
};
```

`groupHistoriesByDate()`는 그룹과 항목을 최신순으로 정렬한다.

```ts
function groupHistoriesByDate(histories: TimelineHistory[]) {
  const groups = new Map<string, TimelineHistory[]>();
  for (const history of [...histories].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))) {
    const label = formatDate(history.createdAt);
    groups.set(label, [...(groups.get(label) ?? []), history]);
  }
  return Array.from(groups.entries()).map(([dateLabel, items]) => ({ dateLabel, items }));
}
```

- [ ] **Step 5: 날짜 전체 보기/접기 구현**

렌더링 직전에 visible groups를 계산한다.

```tsx
const groupedHistories = groupHistoriesByDate(selectedProject.histories);
const visibleGroups = showAllDates ? groupedHistories : groupedHistories.slice(0, 1);
```

날짜 목록 상단에 버튼을 추가한다.

```tsx
{groupedHistories.length > 1 ? (
  <button
    type="button"
    className="rounded-md border border-line px-3 py-1.5 text-xs font-bold text-muted hover:bg-surface-soft"
    onClick={() => setShowAllDates((current) => !current)}
  >
    {showAllDates ? "최신 날짜만 보기" : "날짜 전체 보기"}
  </button>
) : null}
```

그룹별 버튼과 상세 meta 조건부 표시를 추가한다.

```tsx
const isExpanded = expandedDateLabels.has(group.dateLabel);

<button
  type="button"
  className="rounded-md border border-line px-2 py-1 text-xs font-bold text-muted hover:bg-surface-soft"
  onClick={() =>
    setExpandedDateLabels((current) => {
      const next = new Set(current);
      if (next.has(group.dateLabel)) next.delete(group.dateLabel);
      else next.add(group.dateLabel);
      return next;
    })
  }
>
  {isExpanded ? `${group.dateLabel} 간단히 보기` : `${group.dateLabel} 자세히 보기`}
</button>

{isExpanded ? (
  <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px] font-bold text-muted">
    <time>{item.time}</time>
    <span className="badge blue">{item.source}</span>
    <span className="badge green">{item.status}</span>
  </div>
) : null}
```

- [ ] **Step 6: Playwright GREEN 확인**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts --project=chromium-desktop
```

Expected: 날짜 기준, title-only, 최소화/최대화, Open source 새 탭 검증 통과.

---

## Task 5: Slack history 버튼 -> Open source 새 탭 회귀 고정

**Files:**
- Modify: `frontend/e2e/timeline-project-date-groups.spec.ts`
- Verify: `frontend/src/app/timeline/page.tsx`

- [ ] **Step 1: Playwright 시나리오를 명확히 분리**

기존 테스트 안에 아래 흐름을 명시한다.

```ts
await page.getByRole("button", { name: "Open 오전 점검" }).click();
const sourceLink = page.getByRole("link", { name: "Open source" });
await expect(sourceLink).toHaveAttribute("href", "https://slack.example/1");
await expect(sourceLink).toHaveAttribute("target", "_blank");
await expect(sourceLink).toHaveAttribute("rel", /noopener/);
```

- [ ] **Step 2: 실제 새 창 발생도 검증**

속성 검증에 더해 popup 이벤트를 검증한다.

```ts
const popupPromise = page.waitForEvent("popup");
await sourceLink.click();
const popup = await popupPromise;
expect(popup.url()).toBe("https://slack.example/1");
await popup.close();
```

외부 URL navigation이 테스트 환경에서 차단되면 popup URL이 `about:blank`로 남을 수 있다. 이 경우 속성 검증은 반드시 유지하고 popup 검증은 route/mock으로 안정화한다.

- [ ] **Step 3: Playwright 실행**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts --project=chromium-desktop
```

Expected: `1 passed`

---

## Task 6: 프로젝트 탭 원본 근거 Playwright 검증 강화

**Files:**
- Modify: `frontend/e2e/projects-source-links.spec.ts`
- Verify: `frontend/src/app/projects/page.tsx`

- [ ] **Step 1: mock payload를 새 정책에 맞게 수정**

`projects-source-links.spec.ts`의 mock은 `evidence`가 비어 있지 않도록 한다. 이 값은 이제 approved activity source에서 백엔드가 생성한 결과를 의미한다.

```ts
evidence: [
  {
    id: "project-alpha:https://slack.example/activity/1",
    source_id: "https://slack.example/activity/1",
    source_type: "slack",
    title: "Redis 장애 대응 완료",
    source_url: "https://slack.example/activity/1",
    source_snippet: "장애 대응 완료",
    permission_level: "internal",
    timestamp: "2026-05-15T02:00:00Z",
    task_summary: "장애 대응이 완료되었습니다.",
    evidence_reason: "승인된 히스토리 기록입니다.",
  },
]
```

- [ ] **Step 2: 표시/링크 assertion 유지**

```ts
const evidenceLink = page.getByRole("link", { name: "원본 근거 열기 Redis 장애 대응 완료", exact: true });
await expect(evidenceLink).toHaveAttribute("href", "https://slack.example/activity/1");
await expect(evidenceLink).toHaveAttribute("target", "_blank");
await expect(evidenceLink).toHaveAttribute("rel", /noopener/);
```

- [ ] **Step 3: Playwright 실행**

Run:

```powershell
npm.cmd run test:visual -- projects-source-links.spec.ts --project=chromium-desktop
```

Expected: `1 passed`

---

## Task 7: 전체 검증 및 문서 업데이트

**Files:**
- Update: `agent_slack/20260514_project_timeline_rag_progress.md`
- Update: `docs/portfolio-log.md`

- [ ] **Step 1: backend targeted tests**

Run:

```powershell
$env:UV_CACHE_DIR='C:\4th_project\pj04_ParaWorks\.tmp\uv-cache'; uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py -q
```

Expected: 프로젝트 메모리/승인 관련 테스트 통과.

- [ ] **Step 2: frontend lint/build**

Run:

```powershell
npm.cmd run lint
npm.cmd run build
```

Expected: ESLint 통과, Next build 통과.

- [ ] **Step 3: Playwright targeted tests**

Run:

```powershell
npm.cmd run test:visual -- timeline-project-date-groups.spec.ts projects-source-links.spec.ts slack-project-routing-flow.spec.ts --project=chromium-desktop
```

Expected: 타임라인 날짜/접기/원본 링크, 프로젝트 근거 링크, Slack sync -> Review -> Timeline -> Projects 흐름 통과.

- [ ] **Step 4: 작업 기록 업데이트**

`agent_slack/20260514_project_timeline_rag_progress.md`에 한글로 아래 내용을 추가한다.

```markdown
## 2026-05-15 타임라인 실제 source 시각 및 프로젝트 근거 개선

- 타임라인 리스트는 기본적으로 title만 표시하도록 정리했다.
- 타임라인 날짜/시간은 승인 시각이 아니라 Slack source timestamp 기준 `occurred_at`으로 계산한다.
- 날짜 그룹은 기본 최신 날짜만 표시하고, `날짜 전체 보기` 및 날짜별 `자세히 보기/간단히 보기`로 토글할 수 있게 했다.
- 프로젝트 탭의 `연결된 원본 근거`는 legacy project_assignment뿐 아니라 승인된 프로젝트 활동의 source evidence에서도 생성한다.
- Playwright로 Slack history -> Open source 새 탭, 날짜 그룹 토글, 프로젝트 원본 근거 링크를 검증했다.
```

`docs/portfolio-log.md`에는 제품 관점으로 짧게 추가한다.

```markdown
- `fix: 타임라인 source time과 프로젝트 근거 UX 개선`
  - 타임라인을 승인 시각이 아닌 실제 Slack 대화 시각 기준으로 정렬하고, 날짜 단위 compact/detail 토글을 추가했다.
  - 프로젝트 탭이 승인된 활동의 source evidence를 원본 근거로 표시하도록 바꿨다.
  - 검증: backend project memory tests, frontend lint/build, Playwright timeline/project source-link tests 통과.
```

---

## Self-Review

- 요구사항 1: Task 3에서 타임라인 리스트 title-only로 처리한다.
- 요구사항 2: Task 5에서 Slack history 버튼 -> Open source 새 탭을 Playwright로 고정한다.
- 요구사항 3: Task 1, Task 4에서 `occurred_at`을 source timestamp 기준으로 내려주고 프론트가 이 값을 사용한다.
- 요구사항 4: Task 4에서 날짜 전체 보기/최신 날짜만 보기, 날짜별 자세히 보기/간단히 보기를 구현한다.
- 요구사항 5: Task 2, Task 6에서 프로젝트 탭 `연결된 원본 근거`를 approved activity source evidence 기반으로 채운다.
