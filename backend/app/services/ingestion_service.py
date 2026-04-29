"""Ingestion service — embeds chunks and stores them as Sources + SourceSnippets."""
from __future__ import annotations

import hashlib
import logging
from typing import List

from sqlalchemy import select

from app.agents.base_agent import DocumentChunk
from app.core.database import get_db_context
from app.models.source import Source, SourceSnippet, SourceType, PermissionLevel
from app.rag.embeddings import embed_texts

logger = logging.getLogger(__name__)


async def ingest_chunks(chunks: List[DocumentChunk], org_id: str) -> None:
    """
    Embed and store document chunks as Source + SourceSnippet rows.
    Deduplicates by (source_type, source_id, version_hash).
    """
    if not chunks:
        return

    texts = [c['text'] for c in chunks]
    embeddings = await embed_texts(texts)

    async with get_db_context() as db:
        for chunk, embedding in zip(chunks, embeddings):
            version_hash = hashlib.md5(chunk['text'].encode()).hexdigest()

            # Upsert Source (by external_id)
            result = await db.execute(
                select(Source).where(
                    Source.external_id == chunk['source_id'],
                    Source.source_type == chunk['source_type'],
                )
            )
            source = result.scalar_one_or_none()

            if not source:
                source = Source(
                    source_type=SourceType(chunk['source_type']),
                    external_id=chunk['source_id'],
                    source_url=chunk['source_url'],
                    author=chunk['author'],
                    raw_content=chunk['text'],
                    event_time=chunk['timestamp'],
                    project_id=chunk.get('project_id'),
                    permission_level=PermissionLevel(chunk['permission_level']),
                )
                db.add(source)
                await db.flush()
            else:
                # Update permission level if changed
                source.permission_level = PermissionLevel(chunk['permission_level'])

            # Check for existing snippet with same hash (deduplication)
            existing = await db.execute(
                select(SourceSnippet).where(
                    SourceSnippet.source_id == source.id,
                    SourceSnippet.version_hash == version_hash,
                )
            )
            if existing.scalar_one_or_none():
                continue  # Already ingested

            snippet = SourceSnippet(
                source_id=source.id,
                snippet_text=chunk['text'],
                version_hash=version_hash,
                embedding=embedding,
                relevance_score=1.0,
                # Denormalised columns for retriever filtering
                org_id=org_id,
                project_id=chunk.get('project_id'),
                source_type=chunk['source_type'],
                author=chunk['author'],
                event_time=chunk['timestamp'],
                permission_level=chunk['permission_level'],
            )
            db.add(snippet)

        await db.commit()
