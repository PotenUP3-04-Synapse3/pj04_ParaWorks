from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.rag.embeddings import DeterministicHashEmbeddingModel
from backend.app.rag.indexing import (
    PreviewVectorIndexWriter,
    build_rag_index_documents,
    index_vector_documents,
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
    result = index_vector_documents(
        documents=build_rag_index_documents(db),
        writer=writer,
        embedding_model=DeterministicHashEmbeddingModel(dimensions=16),
    )
    return {
        'dry_run': True,
        'indexed_count': result.indexed_count,
        'embedding_dimensions': result.embedding_dimensions,
        'document_ids': result.document_ids,
        'storage_backend': 'preview',
    }
