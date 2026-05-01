from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.db.session import get_db
from backend.app.models import SyncJob, VectorIndexState
from backend.app.rag.embeddings import (
    DeterministicHashEmbeddingModel,
    OpenAIEmbeddingConfig,
    OpenAIEmbeddingModel,
)
from backend.app.rag.indexing import (
    PreviewVectorIndexWriter,
    VectorIndexWriter,
    build_rag_index_documents,
    index_changed_vector_documents,
)
from backend.app.rag.pgvector_store import PgVectorConfig, PgVectorStore

router = APIRouter(prefix='/rag', tags=['rag'])
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post('/reindex')
def reindex_rag_vectors(db: DbSession, settings: AppSettings, dry_run: bool = True) -> dict:
    return _run_reindex(db=db, settings=settings, dry_run=dry_run)


@router.post('/reindex/jobs')
def create_reindex_job(db: DbSession, settings: AppSettings, dry_run: bool = True) -> dict:
    job = SyncJob(
        job_id=f'rag-index-{uuid4().hex}',
        connector_type='rag-index',
        status='running',
        message='indexing running',
        progress_pct=10,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = _run_reindex(db=db, settings=settings, dry_run=dry_run)
    job.status = 'complete'
    job.message = (
        f"indexed={result['indexed_count']} "
        f"skipped={result['skipped_count']} "
        f"saved_embedding_calls={result['saved_embedding_calls']}"
    )
    job.progress_pct = 100
    job.updated_at = datetime.now(UTC)
    db.commit()

    return {
        'job_id': job.job_id,
        'status': job.status,
        **result,
    }


@router.get('/indexing/summary')
def get_rag_indexing_summary(db: DbSession) -> dict:
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
    }


def _run_reindex(*, db: Session, settings: Settings, dry_run: bool) -> dict:
    writer, embedding_model, embedding_model_name, storage_backend, persist_state = _reindex_components(
        db=db,
        settings=settings,
        dry_run=dry_run,
    )
    result = index_changed_vector_documents(
        db=db,
        documents=build_rag_index_documents(db),
        writer=writer,
        embedding_model=embedding_model,
        embedding_model_name=embedding_model_name,
        persist_state=persist_state,
    )
    return {
        'dry_run': dry_run,
        'indexed_count': result.indexed_count,
        'skipped_count': result.skipped_count,
        'saved_embedding_calls': result.saved_embedding_calls,
        'embedding_request_count': result.embedding_request_count,
        'embedding_prompt_tokens': result.embedding_prompt_tokens,
        'embedding_total_tokens': result.embedding_total_tokens,
        'embedding_dimensions': result.embedding_dimensions,
        'document_ids': result.document_ids,
        'skipped_document_ids': result.skipped_document_ids or [],
        'incremental': True,
        'storage_backend': storage_backend,
    }


def _reindex_components(
    *,
    db: Session,
    settings: Settings,
    dry_run: bool,
) -> tuple[VectorIndexWriter, object, str, str, bool]:
    if dry_run:
        return (
            PreviewVectorIndexWriter(),
            DeterministicHashEmbeddingModel(dimensions=16),
            'deterministic-hash:v1',
            'preview',
            False,
        )

    if db.bind is None or db.bind.dialect.name != 'postgresql':
        raise HTTPException(status_code=400, detail='pgvector writes require a PostgreSQL database.')
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail='OPENAI_API_KEY is required for pgvector writes.')

    writer = PgVectorStore(
        session=db,
        config=PgVectorConfig(embedding_dimensions=settings.openai_embedding_dimensions),
    )
    writer.ensure_schema()
    return (
        writer,
        OpenAIEmbeddingModel(
            config=OpenAIEmbeddingConfig(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model,
                dimensions=settings.openai_embedding_dimensions,
                timeout_seconds=settings.openai_embedding_timeout_seconds,
            )
        ),
        settings.openai_embedding_model,
        'pgvector',
        True,
    )


def _job_summary(job: SyncJob) -> dict:
    counters = _parse_index_job_message(job.message)
    return {
        'job_id': job.job_id,
        'connector_type': job.connector_type,
        'status': job.status,
        'message': job.message,
        'progress_pct': job.progress_pct,
        'indexed_count': counters.get('indexed', 0),
        'skipped_count': counters.get('skipped', 0),
        'saved_embedding_calls': counters.get('saved_embedding_calls', 0),
        'updated_at': job.updated_at.isoformat(),
    }


def _parse_index_job_message(message: str) -> dict[str, int]:
    counters: dict[str, int] = {}
    for part in message.split():
        key, separator, value = part.partition('=')
        if separator and value.isdigit():
            counters[key] = int(value)
    return counters
