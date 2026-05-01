from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.rag.embeddings import DeterministicHashEmbeddingModel
from backend.app.rag.indexing import (
    PreviewVectorIndexWriter,
    build_rag_index_documents,
    index_changed_vector_documents,
)

router = APIRouter(prefix='/rag', tags=['rag'])
DbSession = Annotated[Session, Depends(get_db)]


@router.post('/reindex')
def reindex_rag_vectors(db: DbSession, dry_run: bool = True) -> dict:
    if not dry_run:
        raise HTTPException(
            status_code=501,
            detail='pgvector writes require a configured production vector writer.',
        )

    writer = PreviewVectorIndexWriter()
    result = index_changed_vector_documents(
        db=db,
        documents=build_rag_index_documents(db),
        writer=writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=16),
        embedding_model_name='deterministic-hash:v1',
        persist_state=not dry_run,
    )
    return {
        'dry_run': True,
        'indexed_count': result.indexed_count,
        'skipped_count': result.skipped_count,
        'saved_embedding_calls': result.saved_embedding_calls,
        'embedding_dimensions': result.embedding_dimensions,
        'document_ids': result.document_ids,
        'skipped_document_ids': result.skipped_document_ids or [],
        'incremental': True,
        'storage_backend': 'preview',
    }
