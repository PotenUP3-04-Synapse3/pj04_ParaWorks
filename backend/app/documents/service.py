from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.documents.parsers import ParsedDocument, ParsedDocumentChunk, ParserRun
from backend.app.models import Document, DocumentChunk, DocumentVersion, Source


def parsed_document_from_source_event(event: SourceEvent) -> ParsedDocument:
    metadata = event.raw_metadata
    document_version = str(metadata.get('document_version') or 'v1')
    revision_id = str(metadata.get('revision_id') or '')
    content_signature = str(metadata.get('content_signature') or f'{event.source_id}:{document_version}')
    source_snippet = str(metadata.get('source_snippet') or event.body[:240])
    return ParsedDocument(
        source_id=event.source_id,
        source_url=event.source_url,
        source_snippet=source_snippet,
        permission_level=event.permission_level,
        mime_type=str(metadata.get('mime_type') or event.source_type),
        document_version=document_version,
        revision_id=revision_id,
        content_signature=content_signature,
        parser_run=ParserRun(
            parser_name=str(metadata.get('parser_name') or f'{event.source_type}_source_event'),
            parser_status=str(metadata.get('parser_status') or 'parsed'),
            parser_status_reason=_optional_string(metadata.get('parser_status_reason')),
        ),
        chunks=[
            ParsedDocumentChunk(
                chunk_index=0,
                text=event.body,
                source_snippet=source_snippet,
            )
        ],
    )


def persist_parsed_document(
    db: Session,
    *,
    source: Source,
    title: str,
    parsed: ParsedDocument,
    metadata: dict,
) -> list[DocumentChunk]:
    document = db.scalar(select(Document).where(Document.source_id == source.id))
    if document is None:
        document = Document(
            source_id=source.id,
            title=title,
            current_version=parsed.document_version,
        )
        db.add(document)
        db.flush()
    else:
        document.title = title
        document.current_version = parsed.document_version

    version = DocumentVersion(
        document_id=document.id,
        version=parsed.document_version,
        body='\n'.join(chunk.text for chunk in parsed.chunks),
    )
    db.add(version)
    db.flush()

    chunks: list[DocumentChunk] = []
    for parsed_chunk in parsed.chunks:
        chunk = DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=parsed_chunk.chunk_index,
            text=parsed_chunk.text,
            source_snippet=parsed_chunk.source_snippet,
            permission_level=parsed_chunk.permission_level,
            metadata_={
                **metadata,
                **parsed_chunk.metadata,
                'content_hash': parsed_chunk.content_hash,
            },
        )
        db.add(chunk)
        chunks.append(chunk)
    return chunks


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
