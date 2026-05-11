from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.models.source import Document, DocumentVersion, DocumentParserRun, Source

router = APIRouter(prefix='/documents', tags=['documents'])
DbSession = Annotated[Session, Depends(get_db)]

@router.get('')
def list_documents(db: DbSession):
    documents = db.execute(select(Document)).scalars().all()
    result = []
    for doc in documents:
        # Get the latest parser run for this document to show status
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
            **parser_info
        })
    return result

@router.get('/{document_id}/versions')
def get_document_versions(document_id: int, db: DbSession):
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
            **parser_info
        })

    return result
