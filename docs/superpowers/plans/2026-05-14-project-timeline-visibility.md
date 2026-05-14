# Project Timeline and RAG Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Review Queue에서 승인한 메일/문서/프로젝트 관련 지식이 `/projects`, `/timeline`, 그리고 RAG 인덱싱 경로에 일관되게 반영되도록 한다.

**Architecture:** Connector ingestion은 `Source -> Document -> DocumentVersion -> DocumentChunk`를 저장하고, Mail/Document Agent는 DB의 `DocumentChunk + Source`에서 evidence packet을 만든다. Agent output은 trusted knowledge가 아니라 `ReviewItem(status="pending_review")`로 저장되고, 승인 시 `DecisionRecord`, `HistoryEvent`, `TimelineEvent`, `Todo` 같은 approved knowledge 테이블로 승격된다. 이번 작업은 이 승인 경로를 유지하면서, `project_key`와 `source_ids` 메타데이터를 누락 없이 보존하고, RAG 인덱싱이 approved knowledge와 승인된 원본 chunks를 모두 안전하게 포함하도록 고친다.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js App Router, TypeScript, React.

---

## Current Findings

- DB 저장 흐름은 맞다. `backend/app/ingestion/service.py`에서 `Source`를 만들고, `Document`, `DocumentVersion`, `DocumentChunk` 저장 경로로 넘긴다.
- Mail/Document Agent 입력 흐름도 맞다. `backend/app/agents/mail_document_agent/service.py`는 DB의 `DocumentChunk + Source`를 읽어 evidence packet을 만든다.
- Agent 결과는 trusted knowledge로 바로 저장되지 않고 `ReviewItem(status="pending_review")`로 저장된다.
- Review 승인 시 `backend/app/knowledge/promotion.py`에서 `DecisionRecord`, `HistoryEvent`, `TimelineEvent`, `Todo` 같은 approved knowledge 테이블로 승격된다.
- 프로젝트/타임라인 표시 경로에는 누락이 있다. Promoted knowledge record의 `project_key`는 저장되지만, `backend/app/projects/service.py`의 `_approved_memory_records()`가 `ProjectTimelineItem.project_key`로 전달하지 않아 `/api/v1/projects`의 direct project-key matching이 깨진다.
- `/projects`는 현재 visible task를 `memory.evidence`만으로 만들기 때문에, approved `timeline_items`가 API 응답에 있어도 프로젝트 업무/간트/보드/목록에 보이지 않을 수 있다.
- RAG 인덱싱에는 실제 버그가 있다. `backend/app/rag/indexing.py`의 `_chunk_documents()`/`build_rag_index_documents()` 경로가 approved `ReviewItem.payload.source_ids`를 읽으려 하지만 `ReviewItem` import가 없어 `NameError: name 'ReviewItem' is not defined`로 실패한다.
- RAG import를 고쳐도 Mail/Document Agent가 만드는 `ReviewItem.payload`에 `source_ids`가 없어서 승인된 email/document 원본 chunk를 RAG 대상에 포함하는 조건을 만족하지 못한다.
- 설계상 approved knowledge record를 RAG에 넣는 흐름은 존재한다. 미완성인 부분은 "승인된 원본 email/document chunk도 RAG에 넣는 흐름"이다.
- 현재 전체 backend suite는 green이 아니다. 남은 실패는 기존 Slack OAuth PKCE 테스트, Slack fake client 계약, 승인 기반 RAG 인덱싱 정책과 오래된 테스트 기대값 충돌로 분리해서 다룬다. 이 계획의 완료 기준은 관련 targeted tests와 frontend checks green이다.

## Files

- Modify: `backend/app/projects/service.py`
  - Preserve `project_key` on every `ProjectTimelineItem`.
  - Keep connector assignment evidence separate from approved knowledge timeline records.
- Modify: `backend/tests/test_project_memory_api.py`
  - Add regression tests for direct `project_key` matching and review approval to project timeline visibility.
- Modify: `backend/app/rag/indexing.py`
  - Import `ReviewItem`.
  - Keep approved source chunk selection deterministic and permission-preserving.
- Modify: `backend/tests/test_rag_indexing.py`
  - Add/adjust regression tests for approved ReviewItem source chunks and approved knowledge documents.
- Modify: `backend/app/agents/mail_document_agent/service.py`
  - Store `source_ids`, `source_types`, `source_urls`, and optional `source_authors` in generated ReviewItem payloads.
- Modify: `backend/tests/test_mail_document_agent_review_bridge.py`
  - Assert Mail/Document ReviewItems preserve source identity metadata needed by RAG indexing.
- Modify: `frontend/src/lib/api/types.ts`
  - Add `project_key?: string | null` to `ProjectTimelineItem`.
- Modify: `frontend/src/app/projects/page.tsx`
  - Merge `memory.timeline_items` into project task surfaces.
- Verify only: `frontend/src/app/timeline/page.tsx`
  - It should show fixed backend `timeline_items` without behavior changes.
- Modify docs after implementation: `docs/portfolio-log.md`, `docs/superpowers/runbooks/session-handoff.md`

---

### Task 1: Establish Targeted Test Baseline

**Files:**
- Verify: `.venv/pyvenv.cfg`
- Verify: `backend/tests/test_mail_document_agent_review_bridge.py`
- Verify: `backend/tests/test_rag_indexing.py`
- Verify: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: Check Python launcher state**

Run:

```powershell
Get-Content .venv\pyvenv.cfg
where.exe uv
where.exe python
where.exe py
```

Expected:

- A usable `uv` or Python path is available.
- If `.venv\Scripts\python.exe` fails with `Unable to create process`, recreate `.venv` before continuing.

- [ ] **Step 2: Recreate the local virtual environment if needed**

Run only if `.venv\Scripts\python.exe` cannot launch:

```powershell
Rename-Item .venv .venv.broken-20260514
uv sync
```

Expected:

- `uv run python --version` works.
- Test startup errors are gone.

- [ ] **Step 3: Confirm known targeted baseline**

Run:

```powershell
uv run pytest backend/tests/test_mail_document_agent_review_bridge.py::test_mail_document_agent_bridge_filters_sources_and_persists_run -q
uv run pytest backend/tests/test_rag_indexing.py::test_build_rag_index_documents_includes_chunks_and_approved_knowledge -q
```

Expected:

- Mail/Document bridge targeted test passes.
- RAG indexing targeted test fails with `NameError: name 'ReviewItem' is not defined` until Task 7.

---

### Task 2: Add Project Timeline Regression for Direct Project-Key Matching

**Files:**
- Modify: `backend/tests/test_project_memory_api.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: Add failing test**

Append this test to `backend/tests/test_project_memory_api.py`:

```python
def test_projects_api_links_approved_timeline_by_project_key_without_assignment(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        TimelineEvent(
            project_key='seed-ir',
            title='IR pitch deck review completed',
            result_summary='Investor meeting pitch deck review was completed.',
            source_links=['https://drive.mock/drive-ir-deck'],
            source_snippets=['IR pitch deck review is scheduled for next week.'],
            confidence_score=0.9,
            permission_level='internal',
            review_status='approved',
        )
    )
    db_session.commit()

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert response.status_code == 200
    payload = response.json()
    seed_ir = next(project for project in payload['projects'] if project['project_key'] == 'seed-ir')
    assert seed_ir['evidence_count'] == 0
    assert len(seed_ir['timeline_items']) == 1
    assert seed_ir['timeline_items'][0]['title'] == 'IR pitch deck review completed'
    assert seed_ir['timeline_items'][0]['project_key'] == 'seed-ir'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_links_approved_timeline_by_project_key_without_assignment -q
```

Expected:

- FAIL because `/api/v1/projects` does not include the `seed-ir` project or returns no `timeline_items`.

---

### Task 3: Preserve `project_key` in Project Timeline Items

**Files:**
- Modify: `backend/app/projects/service.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: Update `_approved_memory_records()`**

In `backend/app/projects/service.py`, add `project_key=item.project_key` to each `ProjectTimelineItem(...)` created from approved knowledge records:

```python
ProjectTimelineItem(
    id=f'decision_record:{item.id}',
    item_type='decision_record',
    title=item.title,
    summary=item.decision_summary,
    source_links=item.source_links,
    source_snippets=item.source_snippets,
    confidence_score=item.confidence_score,
    permission_level=item.permission_level,
    review_status=item.review_status,
    created_at=item.created_at.isoformat(),
    evidence_reason='Approved decision record is linked to this project workflow.',
    project_key=item.project_key,
)
```

Apply the same `project_key=item.project_key` addition for:

```python
ProjectTimelineItem(id=f'history_event:{item.id}', ...)
ProjectTimelineItem(id=f'timeline_event:{item.id}', ...)
ProjectTimelineItem(id=f'todo:{item.id}', ...)
```

Use these evidence reasons:

```python
'Approved decision record is linked to this project workflow.'
'Approved history record is linked to this project workflow.'
'Approved timeline item is linked to this project workflow.'
'Approved todo is linked to this project workflow.'
```

- [ ] **Step 2: Run direct project-key test**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py::test_projects_api_links_approved_timeline_by_project_key_without_assignment -q
```

Expected:

- PASS.

---

### Task 4: Add Review Approval to Project Timeline Regression

**Files:**
- Modify: `backend/tests/test_project_memory_api.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: Add end-to-end approval test**

Append this test:

```python
def test_approved_review_item_with_project_key_appears_in_project_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    review_item = ReviewItem(
        item_type='timeline_event',
        payload={
            'title': 'K-Tech proposal deadline confirmed',
            'result_summary': 'K-Tech pilot proposal deadline was confirmed for Friday.',
            'project_key': 'k-tech-pilot',
        },
        source_links=['https://slack.mock/archives/C0AUJDZUKA8/p1'],
        source_snippets=['Please update the K-Tech pilot proposal by Friday.'],
        confidence_score=0.88,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(review_item)
    db_session.commit()
    db_session.refresh(review_item)

    approve_response = client.post(
        f'/api/v1/review/{review_item.id}/approve',
        headers={'X-Demo-User': 'demo-admin'},
    )
    assert approve_response.status_code == 200

    projects_response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    assert projects_response.status_code == 200
    ktech = next(project for project in projects_response.json()['projects'] if project['project_key'] == 'k-tech-pilot')
    assert [item['title'] for item in ktech['timeline_items']] == ['K-Tech proposal deadline confirmed']
    assert ktech['timeline_items'][0]['project_key'] == 'k-tech-pilot'
```

- [ ] **Step 2: Run approval regression**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py::test_approved_review_item_with_project_key_appears_in_project_timeline -q
```

Expected:

- PASS after Task 3.

---

### Task 5: Keep Project Evidence Focused on Project Assignments

**Files:**
- Modify: `backend/app/projects/service.py`
- Test: `backend/tests/test_project_memory_api.py`

- [ ] **Step 1: Add regression for knowledge item not becoming fake evidence**

Append this test:

```python
def test_projects_api_does_not_convert_approved_knowledge_into_connector_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    review_item = ReviewItem(
        item_type='history_event',
        payload={
            'title': 'Seed IR follow-up schedule changed',
            'reason': 'Follow-up meeting schedule changed after investor request.',
            'project_key': 'seed-ir',
        },
        source_links=['https://gmail.mock/message-ir'],
        source_snippets=['The next meeting schedule should be adjusted after the investor request.'],
        confidence_score=0.86,
        permission_level='internal',
        status='pending_review',
    )
    db_session.add(review_item)
    db_session.commit()
    db_session.refresh(review_item)

    approve_response = client.post(
        f'/api/v1/review/{review_item.id}/approve',
        headers={'X-Demo-User': 'demo-admin'},
    )
    assert approve_response.status_code == 200

    response = client.get('/api/v1/projects', headers={'X-Demo-User': 'demo-admin'})

    seed_ir = next(project for project in response.json()['projects'] if project['project_key'] == 'seed-ir')
    assert seed_ir['evidence_count'] == 0
    assert len(seed_ir['timeline_items']) == 1
```

- [ ] **Step 2: Split assignment evidence from approved knowledge**

In `backend/app/projects/service.py`, keep `all_approved_items` for active project key discovery, but build connector evidence only from approved `project_assignment` items:

```python
assignment_evidence_items = [
    item
    for item in approved_assignments
    if item.payload.get('project_key') == p_key
]
project_link_items = [
    item
    for item in all_approved_items
    if item.payload.get('project_key') == p_key
]

evidence = _evidence_from_assignments(assignment_evidence_items)
timeline_items = _timeline_for_project(p_key, project_link_items, memory_records)
```

Do not change `_timeline_for_project()` signature.

- [ ] **Step 3: Run project tests**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py -q
```

Expected:

- PASS.

---

### Task 6: Preserve Source Identity in Mail/Document ReviewItems

**Files:**
- Modify: `backend/tests/test_mail_document_agent_review_bridge.py`
- Modify: `backend/app/agents/mail_document_agent/service.py`

- [ ] **Step 1: Add failing source identity assertion**

In `backend/tests/test_mail_document_agent_review_bridge.py`, update `test_mail_document_agent_bridge_filters_sources_and_persists_run` or add a focused test that inspects the created ReviewItem payload:

```python
def test_mail_document_agent_review_item_preserves_source_ids_for_rag(
    db_session: Session,
) -> None:
    # Reuse the existing fixture/helper pattern in this test module to create
    # one gmail/drive source and run create_mail_document_agent_review_items().
    review_items = create_mail_document_agent_review_items(
        db=db_session,
        agent=MailDocumentAgent(model=DeterministicMailDocumentModel()),
        permission_context=PermissionContext(user_id='demo-admin', permission_levels=('internal',)),
        source_window='mail-document:test',
    )

    assert review_items
    payload = review_items[0].payload
    assert payload['source_ids']
    assert all(isinstance(source_id, str) for source_id in payload['source_ids'])
    assert payload['source_types']
    assert set(payload['source_types']).issubset({'gmail', 'gmail_attachment', 'drive', 'calendar'})
```

If the test module already has different helper names, keep the existing helper setup and only add the payload assertions:

```python
assert item.payload['source_ids'] == ['expected-source-id']
assert item.payload['source_types'] == ['gmail']
assert item.payload['source_urls'] == ['https://gmail.mock/message-1']
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_mail_document_agent_review_bridge.py::test_mail_document_agent_review_item_preserves_source_ids_for_rag -q
```

Expected:

- FAIL because Mail/Document ReviewItem payload does not include `source_ids`.

- [ ] **Step 3: Add packet source metadata to payload**

In `backend/app/agents/mail_document_agent/service.py`, before constructing each `ReviewItem`, derive source metadata from `packet.messages`:

```python
source_ids = _unique_strings(message.source_id for message in packet.messages)
source_types = _unique_strings(str(message.metadata.get('source_type') or packet.source_type) for message in packet.messages)
source_urls = _unique_strings(message.source_url for message in packet.messages)
source_authors = _unique_strings(message.author for message in packet.messages if message.author)
```

Add these fields to the ReviewItem payload:

```python
'source_ids': source_ids,
'source_types': source_types,
'source_urls': source_urls,
'source_authors': source_authors,
```

Add this helper near `_estimate_tokens()`:

```python
def _unique_strings(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
```

- [ ] **Step 4: Run Mail/Document bridge tests**

Run:

```powershell
uv run pytest backend/tests/test_mail_document_agent_review_bridge.py -q
```

Expected:

- PASS.

---

### Task 7: Fix Approved ReviewItem Import in RAG Indexing

**Files:**
- Modify: `backend/app/rag/indexing.py`
- Test: `backend/tests/test_rag_indexing.py`

- [ ] **Step 1: Add missing import**

In `backend/app/rag/indexing.py`, update the models import to include `ReviewItem`.

If the file currently imports models like this:

```python
from backend.app.models import (
    DecisionRecord,
    DocumentChunk,
    HistoryEvent,
    Source,
    Todo,
)
```

Change it to:

```python
from backend.app.models import (
    DecisionRecord,
    DocumentChunk,
    HistoryEvent,
    ReviewItem,
    Source,
    Todo,
)
```

Also include `TimelineEvent` if the file uses it and it is not already imported.

- [ ] **Step 2: Run known failing RAG test**

Run:

```powershell
uv run pytest backend/tests/test_rag_indexing.py::test_build_rag_index_documents_includes_chunks_and_approved_knowledge -q
```

Expected:

- It no longer fails with `NameError: name 'ReviewItem' is not defined`.
- If it fails next on policy/expectation mismatch, continue to Task 8.

---

### Task 8: Lock RAG Policy for Approved Original Chunks and Approved Knowledge

**Files:**
- Modify: `backend/tests/test_rag_indexing.py`
- Modify: `backend/app/rag/indexing.py`

- [ ] **Step 1: Add regression for approved source chunks**

Add a focused test in `backend/tests/test_rag_indexing.py` using the module's existing source/chunk fixture style:

```python
def test_build_rag_index_documents_includes_chunks_from_approved_review_source_ids(
    db_session: Session,
) -> None:
    source = Source(
        source_type='gmail',
        source_id='gmail-approved-1',
        source_url='https://gmail.mock/message-approved-1',
        title='Approved customer mail',
        author='owner@example.com',
        participants=['owner@example.com'],
        permission_level='internal',
        raw_metadata={},
    )
    db_session.add(source)
    db_session.flush()
    chunk = DocumentChunk(
        source_id=source.id,
        chunk_index=0,
        text='Customer approved the K-Tech pilot proposal deadline.',
        source_snippet='Customer approved the K-Tech pilot proposal deadline.',
        permission_level='internal',
        metadata_={},
    )
    db_session.add(chunk)
    db_session.add(
        ReviewItem(
            item_type='history_event',
            payload={
                'title': 'Approved source chunk',
                'summary': 'Approved Gmail source should be indexed.',
                'source_ids': ['gmail-approved-1'],
            },
            source_links=['https://gmail.mock/message-approved-1'],
            source_snippets=['Customer approved the K-Tech pilot proposal deadline.'],
            confidence_score=0.88,
            permission_level='internal',
            status='approved',
        )
    )
    db_session.commit()

    documents = build_rag_index_documents(db_session)

    document_ids = {document.document_id for document in documents}
    assert any('gmail-approved-1' in document_id for document_id in document_ids)
    approved_chunk = next(document for document in documents if 'gmail-approved-1' in document.document_id)
    assert approved_chunk.permission_level == 'internal'
    assert 'Customer approved the K-Tech pilot proposal deadline.' in approved_chunk.text
```

- [ ] **Step 2: Run regression**

Run:

```powershell
uv run pytest backend/tests/test_rag_indexing.py::test_build_rag_index_documents_includes_chunks_from_approved_review_source_ids -q
```

Expected:

- PASS after Task 7 if `_chunk_documents()` already implements the approved `source_ids` policy.
- If it fails because payload shape is not handled, update `_chunk_documents()` to read only list-valued string `payload["source_ids"]`.

- [ ] **Step 3: Harden source_ids extraction if needed**

In `backend/app/rag/indexing.py`, use this extraction pattern:

```python
approved_payloads = db.execute(
    select(ReviewItem.payload).where(ReviewItem.status == 'approved')
).scalars().all()

approved_sid_set: set[str] = set()
for payload in approved_payloads:
    if not isinstance(payload, dict):
        continue
    raw_source_ids = payload.get('source_ids')
    if not isinstance(raw_source_ids, list):
        continue
    approved_sid_set.update(
        source_id.strip()
        for source_id in raw_source_ids
        if isinstance(source_id, str) and source_id.strip()
    )
```

Expected:

- RAG chunk indexing includes only source chunks explicitly referenced by approved ReviewItems.
- It does not index all synced email/document chunks by default.

- [ ] **Step 4: Run RAG indexing tests**

Run:

```powershell
uv run pytest backend/tests/test_rag_indexing.py -q
```

Expected:

- RAG indexing targeted tests pass, except any pre-existing tests whose expected policy explicitly conflicts with approval-based source chunk indexing. If a test expects unapproved chunks to be indexed, update that test expectation to the approval-based policy and document the change in the test name.

---

### Task 9: Expose `project_key` in Frontend Types

**Files:**
- Modify: `frontend/src/lib/api/types.ts`

- [ ] **Step 1: Update type**

Modify `ProjectTimelineItem`:

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
  evidence_reason: string;
  project_key?: string | null;
};
```

- [ ] **Step 2: Run TypeScript check**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
```

Expected:

- PASS.

---

### Task 10: Show Approved Timeline Items on Project Task Surfaces

**Files:**
- Modify: `frontend/src/app/projects/page.tsx`
- Verify: `frontend/src/app/timeline/page.tsx`

- [ ] **Step 1: Extend Task type**

In `frontend/src/app/projects/page.tsx`, add `kind` and use clean Korean status labels:

```ts
type Task = {
  id: string;
  title: string;
  owner: string;
  status: "대기" | "진행 중" | "검토" | "완료";
  start: number;
  span: number;
  date: string;
  evidenceReason: string;
  kind: "evidence" | "timeline";
};
```

- [ ] **Step 2: Build tasks from evidence and timeline items**

Replace the start of `projectFromMemory()` with:

```ts
function projectFromMemory(memory: ProjectMemory): Project {
  const evidenceTasks = memory.evidence.map((evidence, index) => ({
    id: evidence.id || `${memory.project_key}:${evidence.source_id}:${index}`,
    title: cleanTaskTitle(evidence.title || evidence.task_summary || evidence.source_snippet, evidence.source_type),
    owner: sourceTypeLabel(evidence.source_type),
    status: taskStatus(evidence.source_type),
    start: Math.min(index + 1, 9),
    span: Math.min(Math.max(2, Math.ceil((evidence.source_snippet.length || 80) / 80)), 4),
    date: formatShortDate(evidence.timestamp),
    evidenceReason: evidence.evidence_reason,
    kind: "evidence" as const,
  }));

  const timelineTasks = memory.timeline_items.map((item, index) => ({
    id: item.id,
    title: cleanTaskTitle(item.title || item.summary || item.source_snippets[0] || "", item.item_type),
    owner: timelineTypeLabel(item.item_type),
    status: "완료" as const,
    start: Math.min(evidenceTasks.length + index + 1, 9),
    span: Math.min(Math.max(2, Math.ceil((item.summary.length || 80) / 80)), 4),
    date: formatShortDate(item.created_at),
    evidenceReason: item.evidence_reason,
    kind: "timeline" as const,
  }));

  const tasks = [...timelineTasks, ...evidenceTasks];
```

Keep the existing returned object, but use `tasks`.

- [ ] **Step 3: Add timeline type label helper**

Add this helper near `sourceTypeLabel()`:

```ts
function timelineTypeLabel(itemType: string) {
  if (itemType === "decision_record") return "승인된 결정";
  if (itemType === "history_event") return "승인된 히스토리";
  if (itemType === "timeline_event") return "승인된 타임라인";
  if (itemType === "todo") return "승인된 할 일";
  return "승인된 업무";
}
```

- [ ] **Step 4: Update status helper and board columns**

Replace `taskStatus()`:

```ts
function taskStatus(sourceType: string): Task["status"] {
  if (sourceType === "drive") return "검토";
  if (sourceType === "slack") return "진행 중";
  return "대기";
}
```

Replace the `columns` value in `BoardView()`:

```ts
const columns: Task["status"][] = ["대기", "진행 중", "검토", "완료"];
```

- [ ] **Step 5: Verify timeline page still consumes approved backend items**

Confirm `frontend/src/app/timeline/page.tsx` still contains:

```ts
histories: project.timeline_items
  .filter((item) => item.review_status === "approved")
  .map(timelineHistoryFromProjectItem),
```

Expected:

- No code change needed in `/timeline` if backend returns matched `timeline_items`.

- [ ] **Step 6: Run frontend checks**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- PASS.

---

### Task 11: Targeted End-to-End Verification

**Files:**
- Verify: `backend/app/api/v1/review.py`
- Verify: `backend/app/api/v1/projects.py`
- Verify: `backend/app/rag/indexing.py`
- Verify: `frontend/src/app/projects/page.tsx`
- Verify: `frontend/src/app/timeline/page.tsx`

- [ ] **Step 1: Run targeted backend tests**

Run:

```powershell
uv run pytest backend/tests/test_project_memory_api.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_rag_indexing.py -q
```

Expected:

- PASS for the targeted tests affected by this plan.
- If unrelated existing Slack OAuth PKCE or fake client contract tests fail in broader suites, do not mix those fixes into this branch.

- [ ] **Step 2: Run frontend checks**

Run:

```powershell
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Expected:

- PASS.

- [ ] **Step 3: Manual API smoke for approved project timeline**

With backend running and an admin/reviewer session available:

```powershell
# 1. Create or locate a pending timeline_event ReviewItem with payload.project_key.
# 2. Approve it through POST /api/v1/review/{item_id}/approve.
# 3. Fetch projects.
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/projects" -Headers @{"X-Demo-User"="demo-admin"}
```

Expected:

- The matching project appears.
- `projects[].timeline_items[]` contains the approved item.
- The item has `project_key`, `review_status="approved"`, `source_links`, and `source_snippets`.

- [ ] **Step 4: Manual RAG indexing smoke**

Run the smallest local RAG build path already used by tests or the local API. If using tests only:

```powershell
uv run pytest backend/tests/test_rag_indexing.py::test_build_rag_index_documents_includes_chunks_from_approved_review_source_ids -q
```

Expected:

- Approved source chunks are included only when their external `Source.source_id` appears in an approved `ReviewItem.payload.source_ids`.
- Approved knowledge records are still included through the existing approved knowledge path.
- Unapproved synced chunks are not indexed by default.

- [ ] **Step 5: Browser smoke**

Open:

```text
http://127.0.0.1:3000/projects
http://127.0.0.1:3000/timeline
```

Expected:

- `/projects` shows approved workflow items in task views.
- `/timeline` shows the same approved workflow items under the matching project.
- Neither page triggers live LLM calls, embedding calls, connector sync, or reindex jobs.

---

### Task 12: Documentation and Commit

**Files:**
- Modify: `docs/portfolio-log.md`
- Modify: `docs/superpowers/runbooks/session-handoff.md`

- [ ] **Step 1: Update portfolio log**

Add a 2026-05-14 entry near the top:

```markdown
## 2026-05-14 Approved Project Timeline and RAG Visibility Fix

- Fixed the approved Review Queue to Project/Timeline display path so promoted
  Decision, History, Timeline, and Todo records preserve `project_key` through
  the shared `/api/v1/projects` response.
- Updated the project workspace to show approved workflow items alongside
  connector assignment evidence, while keeping Review Queue approval as the
  trust boundary.
- Repaired the approval-based RAG source chunk path by importing `ReviewItem`
  in the indexing builder and preserving Mail/Document `source_ids` in
  ReviewItem payloads.
- Verification: targeted project/review/mail-document/RAG backend tests passed;
  frontend TypeScript check and build passed.

Portfolio angle:

- Shows the human-review loop becoming product-visible and retrieval-ready:
  approved evidence-backed work history now appears in project workflow,
  timeline views, and RAG indexing without indexing unapproved synced content.
```

- [ ] **Step 2: Update session handoff**

Add a short note to `docs/superpowers/runbooks/session-handoff.md`:

```markdown
## 2026-05-14 Project/Timeline/RAG Approval Visibility Fix

- Approved knowledge records now preserve `project_key` into project timeline
  API items.
- `/projects` shows approved workflow items from `timeline_items` in addition
  to connector assignment evidence.
- Mail/Document ReviewItems now preserve `source_ids`, allowing approved source
  chunks to enter RAG indexing through the approval-based policy.
- `backend/app/rag/indexing.py` imports `ReviewItem`; the previous
  `NameError: name 'ReviewItem' is not defined` failure is fixed.
- Broader backend suite status should still distinguish unrelated existing
  Slack OAuth PKCE and fake client contract failures from this targeted fix.
- If old local rows still have `timeline_events.project_key = NULL`, rerun
  project classification and approve fresh Review Queue candidates, or use a
  deliberate local-only migration after inspecting source links.
```

- [ ] **Step 3: Check diff**

Run:

```powershell
git diff --check
git status --short
```

Expected:

- No whitespace errors.
- Only intended files are modified.

- [ ] **Step 4: Commit**

Run:

```powershell
git add backend/app/projects/service.py backend/tests/test_project_memory_api.py backend/app/rag/indexing.py backend/tests/test_rag_indexing.py backend/app/agents/mail_document_agent/service.py backend/tests/test_mail_document_agent_review_bridge.py frontend/src/lib/api/types.ts frontend/src/app/projects/page.tsx docs/portfolio-log.md docs/superpowers/runbooks/session-handoff.md
git commit -m "fix: connect approved project memory to timeline and rag"
```

Expected:

- Commit succeeds after all targeted verification passes.

---

## Rollback Notes

- This plan must not change approval authorization, Review Queue statuses, permission filtering, live LLM behavior, connector sync, or default full-corpus indexing policy.
- If `/projects` starts showing too many projects, inspect `active_project_keys` in `backend/app/projects/service.py` and confirm only approved items with explicit `payload.project_key` or knowledge records with `project_key` create project entries.
- If RAG starts indexing too much source content, inspect `_chunk_documents()` and confirm it uses only approved `ReviewItem.payload.source_ids`, not every synced `Source`.
- If old local rows still do not appear, check whether `timeline_events.project_key` is `NULL`. Code fixes new approvals; old rows may need a local data repair after source-link inspection.

## Self-Review

- Spec coverage: The plan covers DB-to-agent ReviewItem metadata preservation, approval promotion, backend project API matching, frontend project task rendering, RAG ReviewItem import, approval-based source chunk indexing, targeted tests, and docs.
- Placeholder scan: No TBD/TODO placeholders are used. Each code change step includes concrete snippets or exact verification commands.
- Type consistency: `ProjectTimelineItem.project_key` is optional in TypeScript and already exists in the Python dataclass. Mail/Document payload `source_ids` is a list of external `Source.source_id` strings, matching the RAG indexing policy.
