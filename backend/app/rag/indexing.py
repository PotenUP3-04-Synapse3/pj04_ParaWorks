import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    DecisionRecord,
    DocumentChunk,
    HistoryEvent,
    ReviewItem,
    Source,
    Todo,
    VectorIndexState,
)
from backend.app.rag.embeddings import EmbeddingBatchResult, EmbeddingModel
from backend.app.rag.vector_store import VectorDocument


class VectorIndexWriter(Protocol):
    def upsert_with_embedding(self, document: VectorDocument, embedding: list[float]) -> None:
        raise NotImplementedError


class EmbeddingBudgetExceededError(ValueError):
    def __init__(self, decision: dict[str, float | int | str | None]) -> None:
        self.decision = decision
        super().__init__('embedding budget exceeded')


@dataclass(frozen=True)
class VectorIndexResult:
    indexed_count: int
    document_ids: list[str]
    embedding_dimensions: int
    skipped_count: int = 0
    skipped_document_ids: list[str] | None = None
    saved_embedding_calls: int = 0
    embedding_request_count: int = 0
    embedding_prompt_tokens: int = 0
    embedding_total_tokens: int = 0
    embedding_budget: dict[str, float | int | str | None] | None = None


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
    embedding_cost_per_1m_tokens: float = 0.0,
    max_embedding_cost_usd: float | None = None,
    enforce_embedding_budget: bool = True,
) -> VectorIndexResult:
    changed_documents: list[tuple[VectorDocument, str, VectorIndexState | None]] = []
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

        changed_documents.append((document, content_hash, state))

    changed_texts = [document.text for document, _, _ in changed_documents]
    budget_decision = estimate_embedding_budget(
        texts=changed_texts,
        embedding_model_name=embedding_model_name,
        cost_per_1m_tokens=embedding_cost_per_1m_tokens,
        max_cost_usd=max_embedding_cost_usd,
    )
    if enforce_embedding_budget and budget_decision['action'] == 'block':
        raise EmbeddingBudgetExceededError(budget_decision)

    batch = _embed_many(embedding_model, changed_texts)
    indexed_document_ids: list[str] = []
    for (document, content_hash, state), embedding in zip(changed_documents, batch.embeddings, strict=True):
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
        embedding_request_count=batch.request_count,
        embedding_prompt_tokens=batch.prompt_tokens,
        embedding_total_tokens=batch.total_tokens,
        embedding_budget=budget_decision,
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


def estimate_embedding_budget(
    *,
    texts: list[str],
    embedding_model_name: str,
    cost_per_1m_tokens: float,
    max_cost_usd: float | None,
) -> dict[str, float | int | str | None]:
    estimated_input_tokens = sum(_estimate_embedding_tokens(text) for text in texts)
    estimated_cost = (
        Decimal(estimated_input_tokens) * Decimal(str(cost_per_1m_tokens)) / Decimal(1_000_000)
    )
    estimated_cost_usd = float(estimated_cost)

    if not texts:
        return {
            'embedding_model': embedding_model_name,
            'changed_document_count': 0,
            'estimated_input_tokens': 0,
            'estimated_cost_usd': 0.0,
            'budget_limit_usd': max_cost_usd,
            'budget_status': 'no_input',
            'action': 'skip',
            'reason': 'no_changed_documents',
        }

    if max_cost_usd is not None and estimated_cost_usd > max_cost_usd:
        return {
            'embedding_model': embedding_model_name,
            'changed_document_count': len(texts),
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_cost_usd': estimated_cost_usd,
            'budget_limit_usd': max_cost_usd,
            'budget_status': 'over_budget',
            'action': 'block',
            'reason': 'estimated_embedding_cost_exceeds_budget',
        }

    return {
        'embedding_model': embedding_model_name,
        'changed_document_count': len(texts),
        'estimated_input_tokens': estimated_input_tokens,
        'estimated_cost_usd': estimated_cost_usd,
        'budget_limit_usd': max_cost_usd,
        'budget_status': 'within_budget' if max_cost_usd is not None else 'not_limited',
        'action': 'run',
        'reason': 'within_embedding_budget',
    }


def build_rag_index_documents(db: Session) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    documents.extend(_chunk_documents(db))
    documents.extend(_decision_documents(db))
    documents.extend(_history_documents(db))
    documents.extend(_todo_documents(db))
    return documents


def _chunk_documents(db: Session) -> list[VectorDocument]:
    # Phase 2: 승인 기반 RAG (Approval-only RAG)
    # 사람이 '승인(approved)'한 ReviewItem에 포함된 source_id 목록만 수집
    approved_payloads = db.execute(
        select(ReviewItem.payload).where(ReviewItem.status == 'approved')
    ).scalars().all()
    
    approved_sid_set = set()
    for p in approved_payloads:
        if isinstance(p, dict) and 'source_ids' in p:
            approved_sid_set.update(p['source_ids'])
            
    if not approved_sid_set:
        return []

    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_id.in_(list(approved_sid_set)))
        .order_by(DocumentChunk.id)
    ).all()
    
    documents: list[VectorDocument] = []
    for chunk, source in rows:
        timestamp = source.raw_metadata.get('ts') or source.created_at.isoformat()
        
        # 메타데이터 보강 (정적 태그 + 동적 태그)
        metadata = {
            'chunk_id': chunk.id,
            'source_pk': source.id,
            'source_id': source.source_id,
            'source_type': source.source_type,
            'author': source.author,
            'author_name': source.raw_metadata.get('author_name') or source.author,
            'channel_name': source.raw_metadata.get('channel_name'),
            'timestamp': str(timestamp),
            'created_at_date': source.raw_metadata.get('created_at_date'),
            'category': chunk.metadata_.get('category'),
            'topic_tag': chunk.metadata_.get('topic_tag'),
            'importance': chunk.metadata_.get('importance'),
            'scenario': source.raw_metadata.get('scenario'),
            **_document_parser_metadata(chunk),
        }
        
        documents.append(
            VectorDocument(
                document_id=f'chunk:{chunk.id}',
                text=chunk.text,
                source_url=source.source_url,
                source_snippet=chunk.source_snippet,
                permission_level=chunk.permission_level,
                metadata=metadata,
            )
        )
    return documents


def _document_parser_metadata(chunk: DocumentChunk) -> dict[str, object]:
    keys = (
        'parser_name',
        'parser_status',
        'parser_status_reason',
        'mime_type',
        'document_version',
        'revision_id',
        'content_signature',
        'content_hash',
        'section_path',
        'page_number',
    )
    return {key: chunk.metadata_.get(key) for key in keys if key in chunk.metadata_}


def _decision_documents(db: Session) -> list[VectorDocument]:
    # 결정사항 테이블 조회 (이미 승인된 것만 저장됨)
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
            text=f'결정사항: {decision.title}\n내용: {decision.decision_summary}',
            source_links=decision.source_links,
            source_snippets=decision.source_snippets,
            permission_level=decision.permission_level,
            timestamp=decision.created_at.isoformat(),
        )
        for decision in decisions
    ]


def _history_documents(db: Session) -> list[VectorDocument]:
    # 기록/공유 테이블 조회
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
            text=f'기록/공유: {event.title}\n내용: {event.reason}',
            source_links=event.source_links,
            source_snippets=event.source_snippets,
            permission_level=event.permission_level,
            timestamp=event.created_at.isoformat(),
        )
        for event in events
    ]


def _todo_documents(db: Session) -> list[VectorDocument]:
    # 할 일 테이블 조회
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
            text=f'할 일: {todo.title}\n우선순위: {todo.priority}\n상세: {todo.priority_reason}',
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
    # 지식 항목 인덱싱 시에도 메타데이터 최대한 보강
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
            'author': 'ParaWorks AI (Verified)',
            'timestamp': timestamp,
        },
    )


def _model_dimensions(embedding_model: EmbeddingModel) -> int:
    return int(getattr(embedding_model, 'dimensions', 0))


def _estimate_embedding_tokens(text: str) -> int:
    if not text:
        return 0
    # Conservative preflight estimate: UTF-8 bytes / 4 tracks English reasonably
    # and errs high for Korean before any paid embedding call is made.
    return max(1, (len(text.encode('utf-8')) + 3) // 4)


def _embed_many(embedding_model: EmbeddingModel, texts: list[str]) -> EmbeddingBatchResult:
    if hasattr(embedding_model, 'embed_many'):
        return embedding_model.embed_many(texts)
    return EmbeddingBatchResult(
        embeddings=[embedding_model.embed(text) for text in texts],
        request_count=len(texts),
    )


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
