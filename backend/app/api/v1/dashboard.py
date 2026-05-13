from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_filters import filter_review_items
from backend.app.db.session import get_db
from backend.app.models import ReviewItem, Source, SyncJob, Todo

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
    
    # 최근 검토 대기 항목 3개
    pending_items = db.scalars(
        select(ReviewItem)
        .where(ReviewItem.status == 'pending_review')
        .order_by(ReviewItem.id.desc())
        .limit(3)
    ).all()

    # 오늘의 할 일 (Todo 타입의 검토 대기 항목 포함)
    todo_items = db.scalars(
        select(ReviewItem)
        .where(ReviewItem.item_type == 'todo')
        .where(ReviewItem.status == 'pending_review')
        .order_by(ReviewItem.id.desc())
        .limit(5)
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
                'title': item.payload.get('title', 'Untitled'),
                'assignee': item.payload.get('assignee', '미지정'),
                'due_date': item.payload.get('due_date', '기한없음'),
                'category': item.payload.get('category', 'N/A'),
            }
            for item in todo_items
        ],
    }
