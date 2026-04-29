"""RAG retriever — pgvector cosine similarity + SQL permission filter."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.rag.embeddings import embed_query

logger = logging.getLogger(__name__)


async def retrieve_chunks(
    query: str,
    filters: Dict[str, Any],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Retrieve source snippets using cosine similarity over pgvector.

    Security: always filters by org_id and permission_levels.
    """
    query_vector = await embed_query(query)
    if not query_vector:
        return []

    # Build SQL filter conditions
    conditions = ['ss.org_id = :org_id']
    params: Dict[str, Any] = {
        'org_id': filters['org_id'],
        'query_vector': query_vector,
        'top_k': top_k,
    }

    # Permission level filter — required, never skipped
    permission_levels = filters.get('permission_levels', ['public'])
    conditions.append('ss.permission_level = ANY(:permission_levels)')
    params['permission_levels'] = permission_levels

    if project_id := filters.get('project_id'):
        conditions.append('ss.project_id = :project_id')
        params['project_id'] = str(project_id)

    if source_types := filters.get('source_types'):
        conditions.append('ss.source_type = ANY(:source_types)')
        params['source_types'] = source_types

    if ts_gte := filters.get('timestamp_gte'):
        conditions.append('ss.event_time >= :ts_gte')
        params['ts_gte'] = ts_gte

    if ts_lte := filters.get('timestamp_lte'):
        conditions.append('ss.event_time <= :ts_lte')
        params['ts_lte'] = ts_lte

    if author := filters.get('author'):
        conditions.append('ss.author ILIKE :author')
        params['author'] = f'%{author}%'

    where_clause = ' AND '.join(conditions)

    # pgvector cosine distance: 1 - (a <=> b)
    sql = text(f"""
        SELECT
            ss.id,
            ss.snippet_text,
            ss.source_id,
            s.source_url,
            s.source_type,
            s.author,
            s.event_time,
            s.permission_level,
            ss.project_id,
            1 - (ss.embedding <=> :query_vector::vector) AS similarity
        FROM source_snippets ss
        JOIN sources s ON s.id = ss.source_id
        WHERE {where_clause}
        ORDER BY ss.embedding <=> :query_vector::vector
        LIMIT :top_k
    """)

    async with get_db_context() as db:
        result = await db.execute(sql, params)
        rows = result.mappings().all()

    return [dict(row) for row in rows]
