from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import SyncJob

router = APIRouter(prefix='/stream', tags=['stream'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('/job-status')
def stream_job_status(job_id: str, db: DbSession) -> StreamingResponse:
    job = db.scalar(select(SyncJob).where(SyncJob.job_id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail='Job not found')

    def events() -> Iterator[str]:
        yield f'event: progress\ndata: {{"job_id":"{job.job_id}","progress_pct":{job.progress_pct},"status":"{job.status}"}}\n\n'
        yield f'event: done\ndata: {{"job_id":"{job.job_id}","status":"{job.status}"}}\n\n'

    return StreamingResponse(events(), media_type='text/event-stream')
