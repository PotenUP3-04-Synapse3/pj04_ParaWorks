from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.source import Document, DocumentParserRun, DocumentVersion

router = APIRouter(prefix='/documents', tags=['documents'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('')
def list_documents(db: DbSession):
    """List all documents with their latest parser status."""
    documents = db.execute(select(Document)).scalars().all()
    result = []
    for doc in documents:
        latest_parser_run = db.execute(
            select(DocumentParserRun)
            .where(DocumentParserRun.document_id == doc.id)
            .order_by(DocumentParserRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        parser_info = {}
        if latest_parser_run:
            parser_info = {
                'revision_id': latest_parser_run.revision_id,
                'parser_name': latest_parser_run.parser_name,
                'parser_status': latest_parser_run.parser_status,
                'parser_status_reason': latest_parser_run.parser_status_reason,
                'chunk_count': latest_parser_run.chunk_count,
            }

        result.append({
            'id': doc.id,
            'source_id': doc.source_id,
            'title': doc.title,
            'current_version': doc.current_version,
            **parser_info,
        })
    return result


@router.get('/parser-stats')
def get_parser_stats(db: DbSession):
    """Return aggregate parser status counts grouped by mime_type and parser_status."""
    rows = db.execute(
        select(
            DocumentParserRun.mime_type,
            DocumentParserRun.parser_status,
            DocumentParserRun.parser_name,
            func.count(DocumentParserRun.id).label('count'),
            func.sum(DocumentParserRun.chunk_count).label('total_chunks'),
        )
        .group_by(
            DocumentParserRun.mime_type,
            DocumentParserRun.parser_status,
            DocumentParserRun.parser_name,
        )
        .order_by(DocumentParserRun.mime_type, DocumentParserRun.parser_status)
    ).all()

    return {
        'stats': [
            {
                'mime_type': row.mime_type,
                'parser_status': row.parser_status,
                'parser_name': row.parser_name,
                'document_count': row.count,
                'total_chunks': row.total_chunks or 0,
            }
            for row in rows
        ],
        'summary': {
            'total_documents': sum(r.count for r in rows),
            'parsed_count': sum(r.count for r in rows if r.parser_status == 'parsed'),
            'metadata_only_count': sum(r.count for r in rows if r.parser_status == 'metadata_only'),
            'error_count': sum(r.count for r in rows if r.parser_status == 'error'),
            'unsupported_count': sum(r.count for r in rows if r.parser_status == 'unsupported'),
        },
    }


@router.get('/{document_id}/versions')
def get_document_versions(document_id: int, db: DbSession):
    """List all versions of a document with their parser info."""
    versions = db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.id.desc())
    ).scalars().all()

    result = []
    for version in versions:
        parser_run = db.execute(
            select(DocumentParserRun)
            .where(DocumentParserRun.document_version_id == version.id)
            .order_by(DocumentParserRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        parser_info = {}
        if parser_run:
            parser_info = {
                'revision_id': parser_run.revision_id,
                'parser_name': parser_run.parser_name,
                'parser_status': parser_run.parser_status,
                'parser_status_reason': parser_run.parser_status_reason,
                'chunk_count': parser_run.chunk_count,
            }

        result.append({
            'id': version.id,
            'version': version.version,
            **parser_info,
        })

    return result


@router.get('/{document_id}/parser-runs')
def get_document_parser_runs(document_id: int, db: DbSession):
    """Return all parser run history for a document, newest first."""
    runs = db.execute(
        select(DocumentParserRun)
        .where(DocumentParserRun.document_id == document_id)
        .order_by(DocumentParserRun.id.desc())
    ).scalars().all()

    return [
        {
            'id': run.id,
            'parser_name': run.parser_name,
            'parser_status': run.parser_status,
            'parser_status_reason': run.parser_status_reason,
            'mime_type': run.mime_type,
            'document_version_label': run.document_version_label,
            'revision_id': run.revision_id,
            'content_signature': run.content_signature,
            'chunk_count': run.chunk_count,
            'started_at': run.started_at.isoformat() if run.started_at else None,
        }
        for run in runs
    ]
