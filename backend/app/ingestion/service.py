from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.knowledge.extractor import build_review_payloads
from backend.app.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    ReviewItem,
    Source,
)


def ingest_events(db: Session, events: list[SourceEvent]) -> int:
    created_chunks: list[DocumentChunk] = []

    for event in events:
        existing_source = db.scalar(select(Source).where(Source.source_id == event.source_id))
        if existing_source is not None:
            continue

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

        document = Document(source_id=source.id, title=event.title, current_version='v1')
        db.add(document)
        db.flush()

        version = DocumentVersion(document_id=document.id, version='v1', body=event.body)
        db.add(version)
        db.flush()

        chunk = DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=0,
            text=event.body,
            source_snippet=event.body[:240],
            permission_level=event.permission_level,
            metadata_={
                **event.raw_metadata,
                'source_id': event.source_id,
                'source_url': event.source_url,
                'source_type': event.source_type,
                'permission_level': event.permission_level,
                'participants': list(event.participants),
                'scenario': event.raw_metadata.get('scenario'),
            },
        )
        db.add(chunk)
        created_chunks.append(chunk)

    review_payloads = build_review_payloads(created_chunks)
    for payload in review_payloads:
        db.add(ReviewItem(status='pending_review', **payload))

    db.commit()
    return len(review_payloads)
