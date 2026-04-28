from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.indexer.chunker import Chunker
from backend.indexer.embedder import Embedder
from backend.models.document import DocumentChunk, DocumentCollection, DocumentVersion
from backend.parsers import ParsedDocument

log = structlog.get_logger(__name__)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:64]


class VectorStore:
    def __init__(self):
        self.chunker = Chunker()
        self.embedder = Embedder()

    async def index_document(
        self,
        session: AsyncSession,
        organization_id: str,
        source_type: str,
        source_id: str,
        source_url: str | None,
        title: str | None,
        mime_type: str | None,
        parsed: ParsedDocument,
        version_label: str | None = None,
        modified_at: datetime | None = None,
    ) -> DocumentCollection:
        """문서 파싱 결과를 청킹 → 임베딩 → pgvector 저장."""

        # 기존 컬렉션 조회 또는 신규 생성
        result = await session.execute(
            text("SELECT id FROM document_collections WHERE source_id = :sid AND source_type = :stype LIMIT 1"),
            {'sid': source_id, 'stype': source_type},
        )
        row = result.fetchone()

        if row:
            collection_id = row[0]
            collection = await session.get(DocumentCollection, collection_id)
        else:
            collection = DocumentCollection(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                source_type=source_type,
                source_id=source_id,
                source_url=source_url,
                title=title,
                mime_type=mime_type,
            )
            session.add(collection)
            await session.flush()
            collection_id = collection.id

        # 버전 diff 계산
        prev_hash_result = await session.execute(
            text(
                "SELECT content_hash, full_text FROM document_versions "
                "WHERE collection_id = :cid ORDER BY created_at DESC LIMIT 1"
            ),
            {'cid': collection_id},
        )
        prev_row = prev_hash_result.fetchone()
        current_hash = _content_hash(parsed.text)

        diff_text: str | None = None
        if prev_row and prev_row[0] != current_hash and prev_row[1]:
            import difflib
            diff_lines = list(difflib.unified_diff(
                prev_row[1].splitlines(),
                parsed.text.splitlines(),
                lineterm='',
            ))
            diff_text = '\n'.join(diff_lines[:500])  # 최대 500줄

        version = DocumentVersion(
            id=str(uuid.uuid4()),
            collection_id=collection_id,
            version_label=version_label or current_hash[:8],
            content_hash=current_hash,
            diff_from_previous=diff_text,
            full_text=parsed.text,
            metadata_=parsed.metadata,
            created_at=modified_at or datetime.now(timezone.utc),
        )
        session.add(version)
        await session.flush()

        # 청킹 & 임베딩
        chunks = self.chunker.chunk(parsed)
        if not chunks:
            return collection

        texts = [c['content'] for c in chunks]
        embeddings = self.embedder.embed(texts)

        # 기존 청크 삭제 (버전 교체)
        await session.execute(
            text("DELETE FROM document_chunks WHERE collection_id = :cid"),
            {'cid': collection_id},
        )

        for i, (chunk_data, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            await session.execute(
                text(
                    "INSERT INTO document_chunks "
                    "(id, collection_id, version_id, content, chunk_index, "
                    " page_number, paragraph_index, metadata, embedding) "
                    "VALUES (:id, :cid, :vid, :content, :cidx, "
                    ":page, :para, :meta::jsonb, :emb::vector)"
                ),
                {
                    'id': chunk_id,
                    'cid': collection_id,
                    'vid': version.id,
                    'content': chunk_data['content'],
                    'cidx': i,
                    'page': chunk_data.get('page_number'),
                    'para': chunk_data.get('paragraph_index'),
                    'meta': str(chunk_data.get('metadata', {})).replace("'", '"'),
                    'emb': str(embedding),
                },
            )

        await session.flush()
        log.info('vector_store.indexed', source_id=source_id, chunks=len(chunks))
        return collection

    async def similarity_search(
        self,
        session: AsyncSession,
        query: str,
        organization_id: str,
        top_k: int = settings.retrieval_top_k,
        permission_levels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """pgvector cosine similarity 검색."""
        query_embedding = self.embedder.embed_one(query)
        vec_str = str(query_embedding)

        # 권한 필터: document_collections → knowledge_assets 또는 direct 권한 체크는
        # 상위 레이어에서 처리, 여기서는 기본 벡터 검색만 수행
        result = await session.execute(
            text(
                "SELECT dc.id, dc.content, dc.collection_id, dc.page_number, dc.paragraph_index, "
                "       docol.source_url, docol.title, docol.source_type, "
                "       1 - (dc.embedding <=> :emb::vector) AS score "
                "FROM document_chunks dc "
                "JOIN document_collections docol ON dc.collection_id = docol.id "
                "WHERE docol.organization_id = :org_id "
                "ORDER BY dc.embedding <=> :emb::vector "
                "LIMIT :k"
            ),
            {'emb': vec_str, 'org_id': organization_id, 'k': top_k},
        )
        rows = result.fetchall()
        return [
            {
                'chunk_id': r[0],
                'content': r[1],
                'collection_id': r[2],
                'page_number': r[3],
                'paragraph_index': r[4],
                'source_url': r[5],
                'title': r[6],
                'source_type': r[7],
                'score': float(r[8]),
            }
            for r in rows
        ]
