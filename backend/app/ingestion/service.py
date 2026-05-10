from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.documents.service import (
    parsed_document_from_source_event,
    persist_parsed_document,
)
from backend.app.knowledge.extractor import build_review_payloads
from backend.app.models import (
    DocumentChunk,
    ReviewItem,
    Source,
)


def ingest_events(db: Session, events: list[SourceEvent]) -> int:
    created_chunks: list[DocumentChunk] = []

    for event in events:
        existing_source = db.scalar(select(Source).where(Source.source_id == event.source_id))
        if existing_source is not None and _same_content_signature(existing_source, event):
            continue

        if existing_source is None:
            source = Source(
                source_type=event.source_type,
                source_id=event.source_id,
                source_url=event.source_url,
                title=event.title,
                author=event.author,
                permission_level=event.permission_level,
                raw_metadata={**event.raw_metadata, 'participants': list(event.participants)},
            )
            db.add(source)
            db.flush()
        else:
            source = existing_source
            source.source_url = event.source_url
            source.title = event.title
            source.author = event.author
            source.permission_level = event.permission_level
            source.raw_metadata = {**event.raw_metadata, 'participants': list(event.participants)}

        parsed_document = parsed_document_from_source_event(event)
        created_chunks.extend(
            persist_parsed_document(
                db,
                source=source,
                title=event.title,
                parsed=parsed_document,
                metadata={
                    **event.raw_metadata,
                    'source_id': event.source_id,
                    'source_url': event.source_url,
                    'source_type': event.source_type,
                    'permission_level': event.permission_level,
                    'participants': list(event.participants),
                    'scenario': event.raw_metadata.get('scenario'),
                },
            )
        )

    review_payloads = build_review_payloads(created_chunks)
    for payload in review_payloads:
        db.add(ReviewItem(status='pending_review', **payload))

    db.commit()
    return len(review_payloads)


def _same_content_signature(source: Source, event: SourceEvent) -> bool:
    existing_signature = (source.raw_metadata or {}).get('content_signature')
    incoming_signature = event.raw_metadata.get('content_signature')
    if existing_signature and incoming_signature:
        return existing_signature == incoming_signature
    return True
