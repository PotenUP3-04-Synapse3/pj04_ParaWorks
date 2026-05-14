from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    DecisionRecord,
    HistoryEvent,
    Project,
    ReviewItem,
    TimelineEvent,
    Todo,
)

PERMISSION_RANK = {'public': 0, 'internal': 1, 'restricted': 2}
SOURCE_TYPE_RANK = {'gmail': 0, 'gmail_attachment': 1, 'drive': 2, 'calendar': 3, 'slack': 4}


@dataclass(frozen=True)
class ProjectEvidence:
    id: str
    source_id: str
    source_type: str
    title: str
    source_url: str
    source_snippet: str
    permission_level: str
    timestamp: str
    task_summary: str
    evidence_reason: str


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
    evidence_reason: str
    project_key: str | None = None


@dataclass(frozen=True)
class ProjectMemory:
    project_key: str
    name: str
    summary: str
    source_types: list[str]
    evidence_count: int
    permission_level: str
    latest_timestamp: str
    pending_review_count: int
    evidence: list[ProjectEvidence]
    timeline_items: list[ProjectTimelineItem]


def build_project_memory(db: Session) -> list[ProjectMemory]:
    approved_assignments = db.scalars(
        select(ReviewItem)
        .where(ReviewItem.item_type == 'project_assignment', ReviewItem.status == 'approved')
        .order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc())
    ).all()
    approved_knowledge_items = db.scalars(
        select(ReviewItem)
        .where(ReviewItem.item_type.in_(['decision_record', 'history_event', 'timeline_event', 'todo']), ReviewItem.status == 'approved')
    ).all()
    pending_counts = _pending_assignment_counts(db)
    memory_records = _approved_memory_records(db)

    db_projects_list = db.scalars(select(Project)).all()
    db_projects = {project.project_key: project for project in db_projects_list}

    active_project_keys = set(db_projects)
    all_approved_items = approved_assignments + approved_knowledge_items
    for item in all_approved_items:
        key = item.payload.get('project_key')
        if isinstance(key, str) and key:
            active_project_keys.add(key)
    for item in memory_records:
        if item.project_key:
            active_project_keys.add(item.project_key)

    projects: list[ProjectMemory] = []
    for project_key in sorted(active_project_keys):
        db_project = db_projects.get(project_key)
        name, base_summary = _project_display(project_key, db_project)

        project_link_items = [
            item
            for item in all_approved_items
            if item.payload.get('project_key') == project_key
        ]
        payload_project_name = next(
            (
                item.payload.get('project_name')
                for item in project_link_items
                if isinstance(item.payload.get('project_name'), str) and item.payload.get('project_name')
            ),
            None,
        )
        if db_project is None and payload_project_name:
            name = payload_project_name

        assignment_evidence_items = [
            item
            for item in approved_assignments
            if item.payload.get('project_key') == project_key
        ]
        evidence = _evidence_from_assignments(assignment_evidence_items)
        timeline_items = _timeline_for_project(project_key, project_link_items, memory_records)

        if not evidence and not timeline_items and db_project is None:
            continue

        permission_levels = [item.permission_level for item in evidence] + [
            item.permission_level for item in timeline_items
        ]
        latest_candidates = [item.timestamp for item in evidence] + [item.created_at for item in timeline_items]
        source_types = sorted(
            {item.source_type for item in evidence},
            key=lambda source_type: SOURCE_TYPE_RANK.get(source_type, 99),
        )
        projects.append(
            ProjectMemory(
                project_key=project_key,
                name=name,
                summary=_project_summary(base_summary, evidence, timeline_items),
                source_types=source_types,
                evidence_count=len(evidence),
                permission_level=_strictest_permission(permission_levels),
                latest_timestamp=max(latest_candidates) if latest_candidates else '',
                pending_review_count=pending_counts.get(project_key, 0),
                evidence=evidence,
                timeline_items=timeline_items,
            )
        )
    return projects


def _project_display(project_key: str, project: Project | None) -> tuple[str, str]:
    if project is not None:
        return project.name, project.summary
    if project_key == 'ad-hoc':
        return '임시 분류(Ad-hoc)', '아직 사용자가 정의한 프로젝트와 연결되지 않은 항목입니다.'
    if project_key.startswith('project-'):
        return project_key.replace('project-', '').replace('-', ' ').title(), 'AI가 임시로 분류한 프로젝트입니다.'
    return f'프로젝트 {project_key.upper()}', 'AI가 임시로 분류한 프로젝트입니다.'


def _pending_assignment_counts(db: Session) -> dict[str, int]:
    pending = db.scalars(
        select(ReviewItem).where(ReviewItem.item_type == 'project_assignment', ReviewItem.status == 'pending_review')
    ).all()
    counts: dict[str, int] = {}
    for item in pending:
        project_key = item.payload.get('project_key')
        if isinstance(project_key, str):
            counts[project_key] = counts.get(project_key, 0) + 1
    return counts


def _evidence_from_assignments(assignments: list[ReviewItem]) -> list[ProjectEvidence]:
    evidence: list[ProjectEvidence] = []
    seen: set[str] = set()
    for item in assignments:
        payload = item.payload or {}
        source_id = str(payload.get('source_id') or f'review-item-{item.id}')
        project_key = str(payload.get('project_key') or 'unknown')
        identity = f'{project_key}:{source_id}'
        if identity in seen:
            continue
        seen.add(identity)
        source_type = str(payload.get('source_type') or 'source')
        task_summary = str(payload.get('task_summary') or payload.get('summary') or payload.get('source_title') or '')
        evidence_reason = str(payload.get('evidence_reason') or '승인된 프로젝트 연결 후보입니다.')
        timestamp = str(payload.get('timestamp') or item.created_at.isoformat())
        evidence.append(
            ProjectEvidence(
                id=identity,
                source_id=source_id,
                source_type=source_type,
                title=_display_title(task_summary, source_type),
                source_url=item.source_links[0] if item.source_links else '',
                source_snippet=item.source_snippets[0] if item.source_snippets else '',
                permission_level=item.permission_level,
                timestamp=timestamp,
                task_summary=task_summary,
                evidence_reason=evidence_reason,
            )
        )
    return sorted(evidence, key=lambda item: (item.timestamp, item.id), reverse=True)


def _approved_memory_records(db: Session) -> list[ProjectTimelineItem]:
    records: list[ProjectTimelineItem] = []
    records.extend(
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
            evidence_reason='승인된 의사결정 기록이 이 프로젝트와 연결되어 있습니다.',
            project_key=item.project_key,
        )
        for item in db.scalars(select(DecisionRecord).where(DecisionRecord.review_status == 'approved')).all()
    )
    records.extend(
        ProjectTimelineItem(
            id=f'history_event:{item.id}',
            item_type='history_event',
            title=item.title,
            summary=item.reason,
            source_links=item.source_links,
            source_snippets=item.source_snippets,
            confidence_score=item.confidence_score,
            permission_level=item.permission_level,
            review_status=item.review_status,
            created_at=item.created_at.isoformat(),
            evidence_reason='승인된 히스토리 기록이 이 프로젝트와 연결되어 있습니다.',
            project_key=item.project_key,
        )
        for item in db.scalars(select(HistoryEvent).where(HistoryEvent.review_status == 'approved')).all()
    )
    records.extend(
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
            evidence_reason='승인된 타임라인 항목이 이 프로젝트와 연결되어 있습니다.',
            project_key=item.project_key,
        )
        for item in db.scalars(select(TimelineEvent).where(TimelineEvent.review_status == 'approved')).all()
    )
    records.extend(
        ProjectTimelineItem(
            id=f'todo:{item.id}',
            item_type='todo',
            title=item.title,
            summary=item.priority_reason,
            source_links=item.source_links,
            source_snippets=item.source_snippets,
            confidence_score=item.confidence_score,
            permission_level=item.permission_level,
            review_status=item.review_status,
            created_at=item.created_at.isoformat(),
            evidence_reason='승인된 할 일이 이 프로젝트와 연결되어 있습니다.',
            project_key=item.project_key,
        )
        for item in db.scalars(select(Todo).where(Todo.review_status == 'approved')).all()
    )
    project_keys = _approved_memory_project_keys(db)
    return [
        replace(record, project_key=project_keys.get(record.id))
        if record.project_key is None and project_keys.get(record.id)
        else record
        for record in records
    ]


def _approved_memory_project_keys(db: Session) -> dict[str, str]:
    keys: dict[str, str] = {}
    for item in db.scalars(select(DecisionRecord).where(DecisionRecord.review_status == 'approved')).all():
        if item.project_key:
            keys[f'decision_record:{item.id}'] = item.project_key
    for item in db.scalars(select(HistoryEvent).where(HistoryEvent.review_status == 'approved')).all():
        if item.project_key:
            keys[f'history_event:{item.id}'] = item.project_key
    for item in db.scalars(select(TimelineEvent).where(TimelineEvent.review_status == 'approved')).all():
        if item.project_key:
            keys[f'timeline_event:{item.id}'] = item.project_key
    for item in db.scalars(select(Todo).where(Todo.review_status == 'approved')).all():
        if item.project_key:
            keys[f'todo:{item.id}'] = item.project_key
    return keys


def _timeline_for_project(
    project_key: str,
    assignments: list[ReviewItem],
    memory_records: list[ProjectTimelineItem],
) -> list[ProjectTimelineItem]:
    project_links = {
        link
        for assignment in assignments
        for link in assignment.source_links
        if assignment.payload.get('project_key') == project_key
    }
    project_source_ids = {
        str(assignment.payload.get('source_id'))
        for assignment in assignments
        if assignment.payload.get('project_key') == project_key and assignment.payload.get('source_id')
    }

    items = []
    for item in memory_records:
        if item.project_key == project_key:
            items.append(item)
            continue

        links_text = ' '.join(item.source_links)
        if project_links.intersection(item.source_links) or any(
            source_id and source_id in links_text for source_id in project_source_ids
        ):
            items.append(item)

    return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)


def _project_summary(base_summary: str, evidence: list[ProjectEvidence], timeline_items: list[ProjectTimelineItem]) -> str:
    if not evidence and not timeline_items:
        return f'{base_summary} 아직 승인된 프로젝트 근거가 없습니다.'
    return (
        f'{base_summary} 승인된 원본 근거 {len(evidence)}건과 '
        f'승인된 활동 {len(timeline_items)}건이 연결되어 있습니다.'
    )


def _display_title(task_summary: str, source_type: str) -> str:
    cleaned = ' '.join(task_summary.split()).strip()
    if cleaned and not cleaned.lower().startswith(('slack message in ', 'slack thread reply in ')):
        return cleaned[:120]
    return f'{_source_type_label(source_type)} evidence'


def _source_type_label(source_type: str) -> str:
    return {
        'gmail': 'Gmail',
        'gmail_attachment': 'Gmail 첨부',
        'drive': 'Drive',
        'calendar': 'Calendar',
        'slack': 'Slack',
    }.get(source_type, 'Source')


def _strictest_permission(levels: list[str]) -> str:
    if not levels:
        return 'internal'
    return max(levels, key=lambda level: PERMISSION_RANK.get(level, 1))
