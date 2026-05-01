from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.connectors.base import Connector
from backend.app.ingestion.service import ingest_events
from backend.app.models import Source, SyncJob


@dataclass(frozen=True)
class ConnectorSyncResult:
    job_id: str
    connector_type: str
    status: str
    fetched_events: int
    created_review_items: int
    skipped_events: int


def sync_connector_events(db: Session, connector: Connector) -> ConnectorSyncResult:
    job = SyncJob(
        job_id=f'{connector.source_type}-{uuid4().hex}',
        connector_type=connector.source_type,
        status='running',
        message='sync running',
        progress_pct=10,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        events = connector.fetch_events()
        existing_source_ids = set(
            db.scalars(
                select(Source.source_id).where(Source.source_id.in_([event.source_id for event in events]))
            ).all()
        )
        created_review_items = ingest_events(db, events)
    except Exception as exc:
        job.status = 'failed'
        job.message = f'failed: {exc}'
        job.progress_pct = 100
        job.updated_at = datetime.now(UTC)
        db.commit()
        raise

    skipped_events = len(existing_source_ids)
    job.status = 'complete'
    job.message = (
        f'fetched={len(events)} '
        f'created_review_items={created_review_items} '
        f'skipped_events={skipped_events}'
    )
    job.progress_pct = 100
    job.updated_at = datetime.now(UTC)
    db.commit()

    return ConnectorSyncResult(
        job_id=job.job_id,
        connector_type=connector.source_type,
        status=job.status,
        fetched_events=len(events),
        created_review_items=created_review_items,
        skipped_events=skipped_events,
    )
