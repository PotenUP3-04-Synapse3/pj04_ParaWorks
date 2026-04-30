from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import ReviewItem, Source, SyncJob

router = APIRouter(prefix='/dashboard', tags=['dashboard'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('')
def get_dashboard(db: DbSession) -> dict:
    source_counts = dict(
        db.execute(select(Source.source_type, func.count(Source.id)).group_by(Source.source_type)).all()
    )
    pending_review_count = db.scalar(
        select(func.count(ReviewItem.id)).where(ReviewItem.status == 'pending_review')
    )
    recent_jobs = db.scalars(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(5)).all()

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
    }
