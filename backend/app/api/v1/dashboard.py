from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_filters import filter_review_items
from backend.app.db.session import get_db
from backend.app.models import (
    DecisionRecord,
    Project,
    ReviewItem,
    Source,
    SyncJob,
    TimelineEvent,
    Todo,
)
from backend.app.projects import build_project_memory

router = APIRouter(prefix='/dashboard', tags=['dashboard'])
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get('')
def get_dashboard(db: DbSession, settings: AppSettings) -> dict:
    source_counts = dict(
        db.execute(select(Source.source_type, func.count(Source.id)).group_by(Source.source_type)).all()
    )
    if settings.paraworks_demo_mode:
        pending_review_count = db.scalar(
            select(func.count(ReviewItem.id)).where(ReviewItem.status == 'pending_review')
        )
    else:
        pending_review_items = db.scalars(
            select(ReviewItem).where(ReviewItem.status == 'pending_review')
        ).all()
        pending_review_count = len(filter_review_items(pending_review_items))
    recent_jobs = db.scalars(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(5)).all()

    pending_items = db.scalars(
        select(ReviewItem)
        .where(ReviewItem.status == 'pending_review')
        .order_by(ReviewItem.id.desc())
        .limit(3)
    ).all()

    today = _today_kst()
    todo_candidates = db.scalars(
        select(Todo)
        .where(Todo.review_status == 'approved')
        .where(Todo.completed_at.is_(None))
        .order_by(Todo.id.desc())
    ).all()
    todo_items = sorted(
        [item for item in todo_candidates if _is_due_from_today(item.due_date or '', today)],
        key=lambda item: (item.due_date or '', item.id),
    )[:5]
    project_names = _project_names_by_key(db)

    assigned_projects = build_project_memory(db)

    recent_decisions = db.scalars(
        select(DecisionRecord)
        .where(DecisionRecord.review_status == 'approved')
        .order_by(DecisionRecord.created_at.desc())
        .limit(3)
    ).all()

    recent_timeline = db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.review_status == 'approved')
        .order_by(TimelineEvent.created_at.desc())
        .limit(3)
    ).all()

    return {
        'source_counts': source_counts,
        'pending_review_count': pending_review_count or 0,
        'recent_jobs': [
            {
                'job_id': job.job_id,
                'connector_type': job.connector_type,
                'status': job.status,
                'message': job.message,
                'progress_pct': job.progress_pct,
            }
            for job in recent_jobs
        ],
        'pending_items': [
            {
                'id': item.id,
                'title': item.payload.get('title', 'Untitled'),
                'item_type': item.item_type,
                'category': item.payload.get('category', 'Ad-hoc'),
                'confidence_score': item.confidence_score,
            }
            for item in pending_items
        ],
        'today_todos': [
            {
                'id': item.id,
                'title': item.title,
                'assignee': item.assignee or '미정',
                'due_date': item.due_date or '기한 없음',
                'category': project_names.get(item.project_key or '', '프로젝트 미지정'),
                'priority': item.priority or 'medium',
                'completed_at': item.completed_at.isoformat() if item.completed_at else None,
            }
            for item in todo_items
        ],
        'assigned_projects': [
            {
                'project_key': project.project_key,
                'name': project.name,
                'summary': project.summary,
                'evidence_count': project.evidence_count,
                'activity_count': len(project.activity_items),
                'pending_review_count': project.pending_review_count,
                'latest_timestamp': project.latest_timestamp,
                'permission_level': project.permission_level,
            }
            for project in assigned_projects
        ],
        'recent_decisions': [
            {
                'id': d.id,
                'title': d.title,
                'summary': d.decision_summary,
                'created_at': d.created_at.isoformat(),
            }
            for d in recent_decisions
        ],
        'recent_timeline': [
            {
                'id': t.id,
                'title': t.title,
                'summary': t.result_summary,
                'created_at': t.created_at.isoformat(),
                'confidence_score': t.confidence_score,
                'source_links': t.source_links,
            }
            for t in recent_timeline
        ],
    }


def _today_kst() -> str:
    return datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()


def _project_names_by_key(db: Session) -> dict[str, str]:
    projects = db.scalars(select(Project)).all()
    return {project.project_key: project.name for project in projects}


def _is_due_from_today(due_date: str, today: str) -> bool:
    if len(due_date) != 10:
        return False
    return due_date >= today
