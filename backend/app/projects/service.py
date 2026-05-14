from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    DecisionRecord,
    HistoryEvent,
    ReviewItem,
    TimelineEvent,
    Todo,
)
from backend.app.projects.classifier import CANONICAL_PROJECTS

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
    
    # 1. 리뷰 항목에서 가져오는 새 방식의 ReviewItem들 (Phase 2로 project_key가 payload에 포함된 경우)
    approved_knowledge_items = db.scalars(
        select(ReviewItem)
        .where(ReviewItem.item_type.in_(['decision_record', 'history_event', 'timeline_event', 'todo']), ReviewItem.status == 'approved')
    ).all()
    
    pending_counts = _pending_assignment_counts(db)
    memory_records = _approved_memory_records(db)

    # 모든 프로젝트 키 수집
    active_project_keys = set()
    
    # 통합된 모든 승인 항목
    all_approved_items = approved_assignments + approved_knowledge_items
    
    for item in all_approved_items:
        key = item.payload.get('project_key')
        if key: active_project_keys.add(key)
    
    for item in memory_records:
        if item.project_key:
            active_project_keys.add(item.project_key)

    projects: list[ProjectMemory] = []
    
    # Canonical 프로젝트와 동적 프로젝트 매핑용 헬퍼 함수
    from backend.app.projects.classifier import project_by_key

    for p_key in sorted(active_project_keys):
        canonical = project_by_key(p_key)
        
        # 이름 변환: ad-hoc 이면 '미분류 업무', project- 로 시작하면 태그 이름 복원
        if canonical:
            name = canonical.name
        elif p_key == 'ad-hoc':
            name = '기타 업무 (Ad-hoc)'
        elif p_key.startswith('project-'):
            name = p_key.replace('project-', '').replace('-', ' ').title()
        else:
            name = f"프로젝트 {p_key.upper()}"
            
        base_summary = canonical.summary if canonical else "AI에 의해 분류된 동적 프로젝트입니다."
        
        assignments = [
            item
            for item in all_approved_items
            if item.payload.get('project_key') == p_key
        ]
        
        evidence = _evidence_from_assignments(assignments)
        timeline_items = _timeline_for_project(p_key, assignments, memory_records)
        
        # evidence나 timeline_items가 없으면 스킵
        if not evidence and not timeline_items:
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
                project_key=p_key,
                name=name,
                summary=_project_summary(base_summary, evidence, timeline_items),
                source_types=source_types,
                evidence_count=len(evidence),
                permission_level=_strictest_permission(permission_levels),
                latest_timestamp=max(latest_candidates) if latest_candidates else '',
                pending_review_count=pending_counts.get(p_key, 0),
                evidence=evidence,
                timeline_items=timeline_items,
            )
        )
    return projects


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
            evidence_reason='승인된 결정 기록의 source link가 프로젝트 evidence와 연결됩니다.',
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
            evidence_reason='승인된 히스토리의 source link가 프로젝트 evidence와 연결됩니다.',
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
            evidence_reason='승인된 타임라인 항목의 source link가 프로젝트 evidence와 연결됩니다.',
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
            evidence_reason='승인된 할 일의 source link가 프로젝트 evidence와 연결됩니다.',
        )
        for item in db.scalars(select(Todo).where(Todo.review_status == 'approved')).all()
    )
    return records


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
        # Phase 3 이후 데이터는 project_key가 명시적으로 존재함
        if item.project_key == project_key:
            items.append(item)
            continue
            
        # 레거시 데이터 폴백: source_links나 source_id 기반 매칭
        if project_links.intersection(item.source_links) or any(
            source_id and source_id in ' '.join(item.source_links) for source_id in project_source_ids
        ):
            items.append(item)

    return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)


def _project_summary(base_summary: str, evidence: list[ProjectEvidence], timeline_items: list[ProjectTimelineItem]) -> str:
    if not evidence and not timeline_items:
        return f'{base_summary} 아직 승인된 프로젝트 evidence가 없습니다.'
    return (
        f'{base_summary} 승인된 evidence {len(evidence)}건과 '
        f'워크플로우 항목 {len(timeline_items)}건이 연결되어 있습니다.'
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
