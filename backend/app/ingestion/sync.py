from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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
        if hasattr(connector, 'fetch_events_since'):
            events = connector.fetch_events_since(_latest_cursors_by_partition(db, connector.source_type))
        else:
            events = connector.fetch_events()
        skipped_events = _count_same_content_signature_events(db, events)
        created_review_items = ingest_events(db, events)
    except Exception as exc:
        job.status = 'failed'
        job.message = f'failed: {exc}'
        job.progress_pct = 100
        job.updated_at = datetime.now(UTC)
        db.commit()
        raise

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


def _latest_cursors_by_partition(db: Session, source_type: str) -> dict[str, str]:
    latest: dict[str, tuple[tuple[int, object], str]] = {}
    sources = db.scalars(select(Source).where(Source.source_type == source_type)).all()
    for source in sources:
        raw_metadata = source.raw_metadata or {}
        partition = raw_metadata.get('sync_partition')
        cursor = raw_metadata.get('sync_cursor')
        if not isinstance(partition, str) or not isinstance(cursor, str) or not cursor:
            partition = raw_metadata.get('channel_id')
            cursor = raw_metadata.get('ts')
        if not isinstance(partition, str) or not isinstance(cursor, str) or not cursor:
            continue
        cursor_value = _cursor_sort_key(cursor)
        previous = latest.get(partition)
        if previous is None or cursor_value > previous[0]:
            latest[partition] = (cursor_value, cursor)
    return {partition: cursor for partition, (_, cursor) in latest.items()}


def _count_same_content_signature_events(db: Session, events: list) -> int:
    if not events:
        return 0
    sources_by_id = {
        source.source_id: source
        for source in db.scalars(
            select(Source).where(Source.source_id.in_([event.source_id for event in events]))
        ).all()
    }
    skipped = 0
    for event in events:
        source = sources_by_id.get(event.source_id)
        if source is None:
            continue
        existing_signature = (source.raw_metadata or {}).get('content_signature')
        incoming_signature = event.raw_metadata.get('content_signature')
        if existing_signature and incoming_signature:
            if existing_signature == incoming_signature:
                skipped += 1
        else:
            skipped += 1
    return skipped


def _cursor_sort_key(cursor: str) -> tuple[int, object]:
    try:
        return (0, Decimal(cursor))
    except InvalidOperation:
        pass
    try:
        normalized = cursor.replace('Z', '+00:00')
        return (1, datetime.fromisoformat(normalized).astimezone(UTC))
    except ValueError:
        return (2, cursor)
