from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import DemoUser, require_admin_user
from backend.app.db.session import get_db
from backend.app.models import SyncJob, VectorIndexState
from backend.app.rag.reindexing import ReindexConfigurationError, run_reindex
from backend.app.services.audit import record_audit_log
from backend.app.tasks.rag_indexing import (
    enqueue_rag_reindex_job,
    execute_rag_reindex_job,
)

router = APIRouter(prefix='/rag', tags=['rag'])
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]


@router.post('/reindex')
def reindex_rag_vectors(db: DbSession, settings: AppSettings, user: AdminUser, dry_run: bool = True) -> dict:
    try:
        result = run_reindex(db=db, settings=settings, dry_run=dry_run)
    except ReindexConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_log(
        db=db,
        actor=user,
        action='rag.reindex.run',
        target_type='rag-index',
        target_id='direct',
        metadata={
            'dry_run': dry_run,
            'indexed_count': result.get('indexed_count', 0),
            'skipped_count': result.get('skipped_count', 0),
            'embedding_request_count': result.get('embedding_request_count', 0),
        },
    )
    db.commit()
    return result


@router.post('/reindex/jobs')
def create_reindex_job(db: DbSession, settings: AppSettings, user: AdminUser, dry_run: bool = True) -> dict:
    job = SyncJob(
        job_id=f'rag-index-{uuid4().hex}',
        connector_type='rag-index',
        status='queued',
        message='queued',
        progress_pct=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    record_audit_log(
        db=db,
        actor=user,
        action='rag.reindex.job.create',
        target_type='rag-index',
        target_id=job.job_id,
        metadata={'dry_run': dry_run, 'eager': settings.celery_task_always_eager},
    )
    db.commit()

    if settings.celery_task_always_eager:
        try:
            return execute_rag_reindex_job(
                db=db,
                settings=settings,
                job_id=job.job_id,
                dry_run=dry_run,
            )
        except ReindexConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    enqueue_rag_reindex_job(job_id=job.job_id, dry_run=dry_run)
    return {
        'job_id': job.job_id,
        'status': job.status,
        'dry_run': dry_run,
    }


@router.get('/reindex/jobs/{job_id}')
def get_reindex_job(job_id: str, db: DbSession, _: AdminUser) -> dict:
    job = db.scalar(select(SyncJob).where(SyncJob.job_id == job_id, SyncJob.connector_type == 'rag-index'))
    if job is None:
        raise HTTPException(status_code=404, detail='RAG indexing job not found')
    return _job_summary(job)


@router.get('/indexing/summary')
def get_rag_indexing_summary(db: DbSession, settings: AppSettings, _: AdminUser) -> dict:
    state_counts = dict(
        db.execute(
            select(VectorIndexState.status, func.count(VectorIndexState.id))
            .group_by(VectorIndexState.status)
            .order_by(VectorIndexState.status)
        ).all()
    )
    latest_jobs = db.scalars(
        select(SyncJob)
        .where(SyncJob.connector_type == 'rag-index')
        .order_by(SyncJob.updated_at.desc(), SyncJob.id.desc())
        .limit(5)
    ).all()
    return {
        'state_counts': state_counts,
        'latest_jobs': [_job_summary(job) for job in latest_jobs],
        'cost_policy': {
            'embedding_model': settings.openai_embedding_model,
            'embedding_input_cost_per_1m_tokens': settings.openai_embedding_input_cost_per_1m_tokens,
            'max_estimated_embedding_cost_usd': settings.rag_embedding_max_estimated_cost_usd,
            'preflight_budget_gate': settings.rag_embedding_max_estimated_cost_usd is not None,
            'incremental_hash_skip': True,
        },
    }


def _job_summary(job: SyncJob) -> dict:
    counters = _parse_index_job_message(job.message)
    failure_reason = _parse_failure_reason(job.message) if job.status == 'failed' else None
    return {
        'job_id': job.job_id,
        'connector_type': job.connector_type,
        'status': job.status,
        'message': job.message,
        'failure_reason': failure_reason,
        'progress_pct': job.progress_pct,
        'indexed_count': counters.get('indexed', 0),
        'skipped_count': counters.get('skipped', 0),
        'saved_embedding_calls': counters.get('saved_embedding_calls', 0),
        'updated_at': job.updated_at.isoformat(),
    }


def _parse_failure_reason(message: str) -> str | None:
    prefix = 'failed:'
    if message.lower().startswith(prefix):
        return message[len(prefix) :].strip() or None
    return message or None


def _parse_index_job_message(message: str) -> dict[str, int]:
    counters: dict[str, int] = {}
    for part in message.split():
        key, separator, value = part.partition('=')
        if separator and value.isdigit():
            counters[key] = int(value)
    return counters
