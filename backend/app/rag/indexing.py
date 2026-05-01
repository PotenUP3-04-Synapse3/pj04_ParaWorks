import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    DecisionRecord,
    DocumentChunk,
    HistoryEvent,
    Source,
    Todo,
    VectorIndexState,
)
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.rag.vector_store import VectorDocument


class VectorIndexWriter(Protocol):
    def upsert_with_embedding(self, document: VectorDocument, embedding: list[float]) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class VectorIndexResult:
    indexed_count: int
    document_ids: list[str]
    embedding_dimensions: int
    skipped_count: int = 0
    skipped_document_ids: list[str] | None = None
    saved_embedding_calls: int = 0


class PreviewVectorIndexWriter:
    def __init__(self) -> None:
        self.upserts: list[tuple[VectorDocument, list[float]]] = []

    def upsert_with_embedding(self, document: VectorDocument, embedding: list[float]) -> None:
        self.upserts.append((document, embedding))


def index_vector_documents(
    *,
    documents: list[VectorDocument],
    writer: VectorIndexWriter,
    embedding_model: EmbeddingModel,
) -> VectorIndexResult:
    document_ids: list[str] = []
    embedding_dimensions = 0
    for document in documents:
        embedding = embedding_model.embed(document.text)
        embedding_dimensions = len(embedding)
        writer.upsert_with_embedding(document, embedding)
        document_ids.append(document.document_id)

    return VectorIndexResult(
        indexed_count=len(document_ids),
        document_ids=document_ids,
        embedding_dimensions=embedding_dimensions or _model_dimensions(embedding_model),
        skipped_document_ids=[],
    )


def index_changed_vector_documents(
    *,
    db: Session,
    documents: list[VectorDocument],
    writer: VectorIndexWriter,
    embedding_model: EmbeddingModel,
    embedding_model_name: str,
    persist_state: bool = True,
) -> VectorIndexResult:
    indexed_document_ids: list[str] = []
    skipped_document_ids: list[str] = []
    embedding_dimensions = _model_dimensions(embedding_model)

    for document in documents:
        content_hash = compute_vector_document_hash(document)
        state = _get_index_state(
            db=db,
            document_id=document.document_id,
            embedding_model_name=embedding_model_name,
        )
        if state and state.status == 'indexed' and state.content_hash == content_hash:
            skipped_document_ids.append(document.document_id)
            continue

        embedding = embedding_model.embed(document.text)
        embedding_dimensions = len(embedding)
        writer.upsert_with_embedding(document, embedding)
        indexed_document_ids.append(document.document_id)
        if persist_state:
            _upsert_index_state(
                db=db,
                state=state,
                document=document,
                embedding_model_name=embedding_model_name,
                embedding_dimensions=embedding_dimensions,
                content_hash=content_hash,
            )

    if persist_state:
        db.commit()

    return VectorIndexResult(
        indexed_count=len(indexed_document_ids),
        document_ids=indexed_document_ids,
        embedding_dimensions=embedding_dimensions,
        skipped_count=len(skipped_document_ids),
        skipped_document_ids=skipped_document_ids,
        saved_embedding_calls=len(skipped_document_ids),
    )


def compute_vector_document_hash(document: VectorDocument) -> str:
    payload = {
        'document_id': document.document_id,
        'text': document.text,
        'source_url': document.source_url,
        'source_snippet': document.source_snippet,
        'permission_level': document.permission_level,
        'metadata': document.metadata,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')
    return sha256(encoded).hexdigest()


def build_rag_index_documents(db: Session) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    documents.extend(_chunk_documents(db))
    documents.extend(_decision_documents(db))
    documents.extend(_history_documents(db))
    documents.extend(_todo_documents(db))
    return documents


def _chunk_documents(db: Session) -> list[VectorDocument]:
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .order_by(DocumentChunk.id)
    ).all()
    documents: list[VectorDocument] = []
    for chunk, source in rows:
        timestamp = source.raw_metadata.get('ts') or source.created_at.isoformat()
        documents.append(
            VectorDocument(
                document_id=f'chunk:{chunk.id}',
                text=chunk.text,
                source_url=source.source_url,
                source_snippet=chunk.source_snippet,
                permission_level=chunk.permission_level,
                metadata={
                    'chunk_id': chunk.id,
                    'source_pk': source.id,
                    'source_id': source.source_id,
                    'source_type': source.source_type,
                    'author': source.author,
                    'timestamp': str(timestamp),
                    'scenario': source.raw_metadata.get('scenario'),
                },
            )
        )
    return documents


def _decision_documents(db: Session) -> list[VectorDocument]:
    decisions = db.scalars(
        select(DecisionRecord)
        .where(DecisionRecord.review_status == 'approved')
        .order_by(DecisionRecord.id)
    ).all()
    return [
        _knowledge_document(
            document_id=f'decision_record:{decision.id}',
            source_type='decision_record',
            title=decision.title,
            text=f'{decision.title}\n{decision.decision_summary}',
            source_links=decision.source_links,
            source_snippets=decision.source_snippets,
            permission_level=decision.permission_level,
            timestamp=decision.created_at.isoformat(),
        )
        for decision in decisions
    ]


def _history_documents(db: Session) -> list[VectorDocument]:
    events = db.scalars(
        select(HistoryEvent)
        .where(HistoryEvent.review_status == 'approved')
        .order_by(HistoryEvent.id)
    ).all()
    return [
        _knowledge_document(
            document_id=f'history_event:{event.id}',
            source_type='history_event',
            title=event.title,
            text=f'{event.title}\n{event.reason}',
            source_links=event.source_links,
            source_snippets=event.source_snippets,
            permission_level=event.permission_level,
            timestamp=event.created_at.isoformat(),
        )
        for event in events
    ]


def _todo_documents(db: Session) -> list[VectorDocument]:
    todos = db.scalars(
        select(Todo)
        .where(Todo.review_status == 'approved')
        .order_by(Todo.id)
    ).all()
    return [
        _knowledge_document(
            document_id=f'todo:{todo.id}',
            source_type='todo',
            title=todo.title,
            text=f'{todo.title}\n{todo.priority}\n{todo.priority_reason}',
            source_links=todo.source_links,
            source_snippets=todo.source_snippets,
            permission_level=todo.permission_level,
            timestamp=todo.created_at.isoformat(),
        )
        for todo in todos
    ]


def _knowledge_document(
    *,
    document_id: str,
    source_type: str,
    title: str,
    text: str,
    source_links: list[str],
    source_snippets: list[str],
    permission_level: str,
    timestamp: str,
) -> VectorDocument:
    return VectorDocument(
        document_id=document_id,
        text=text,
        source_url=source_links[0] if source_links else f'knowledge://{document_id}',
        source_snippet=source_snippets[0] if source_snippets else text[:240],
        permission_level=permission_level,
        metadata={
            'knowledge_id': document_id,
            'source_type': source_type,
            'title': title,
            'author': None,
            'timestamp': timestamp,
        },
    )


def _model_dimensions(embedding_model: EmbeddingModel) -> int:
    return int(getattr(embedding_model, 'dimensions', 0))


def _get_index_state(
    *,
    db: Session,
    document_id: str,
    embedding_model_name: str,
) -> VectorIndexState | None:
    return db.scalar(
        select(VectorIndexState).where(
            VectorIndexState.document_id == document_id,
            VectorIndexState.embedding_model == embedding_model_name,
        )
    )


def _upsert_index_state(
    *,
    db: Session,
    state: VectorIndexState | None,
    document: VectorDocument,
    embedding_model_name: str,
    embedding_dimensions: int,
    content_hash: str,
) -> None:
    now = datetime.now(UTC)
    if state is None:
        db.add(
            VectorIndexState(
                document_id=document.document_id,
                embedding_model=embedding_model_name,
                embedding_dimensions=embedding_dimensions,
                content_hash=content_hash,
                status='indexed',
                last_error=None,
                indexed_at=now,
            )
        )
        return

    state.embedding_dimensions = embedding_dimensions
    state.content_hash = content_hash
    state.status = 'indexed'
    state.last_error = None
    state.indexed_at = now
