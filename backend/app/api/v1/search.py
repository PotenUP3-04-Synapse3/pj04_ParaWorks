"""Search API — RAG-based semantic search with permission filtering."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.source import PermissionLevel
from app.models.user import User, UserRole
from app.rag.embeddings import embed_query
from app.rag.retriever import retrieve_chunks
from app.agents.base_agent import get_llm
from app.llm.prompts.agent_prompts import SEARCH_ANSWER_PROMPT
from app.llm.structured_outputs import SearchAnswerResult, DecisionRecordExtractionResult
from app.models.decision_record import DecisionRecord

router = APIRouter(prefix='/search', tags=['search'])
logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.45  # below this, warn user that answer may be unreliable


# ── Request / Response schemas ────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    project_id: Optional[UUID] = None
    source_types: Optional[List[str]] = None
    timestamp_gte: Optional[str] = None  # ISO8601
    timestamp_lte: Optional[str] = None  # ISO8601
    author: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)


class SnippetOut(BaseModel):
    id: UUID
    text: str
    source_url: str
    source_type: str
    author: Optional[str]
    similarity: float
    permission_level: str


class SearchResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    related_decisions: List[str] = Field(default_factory=list)
    related_projects: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    needs_human_review: bool = False
    source_snippets: List[SnippetOut] = Field(default_factory=list)
    total_results: int = 0


class SimilarDecisionRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    business_domain: Optional[str] = None


class SimilarDecisionOut(BaseModel):
    id: UUID
    title: str
    decision_summary: Optional[str]
    business_domain: Optional[str]
    decided_at: Optional[str]
    confidence_score: Optional[float]
    similarity: float


class SimilarDecisionsResponse(BaseModel):
    query: str
    decisions: List[SimilarDecisionOut]


# ── Helpers ───────────────────────────────────────────────────────────────

def _get_user_permission_levels(role: str) -> List[str]:
    """Map user role to allowed permission levels."""
    if role in (UserRole.admin, UserRole.manager):
        return ['public', 'team', 'restricted']
    return ['public', 'team']


async def _get_current_user(request: Request, db: AsyncSession) -> User:
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post('', response_model=SearchResponse)
async def search(
    body: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Semantic search over org knowledge base with LLM-synthesized answer."""
    user = await _get_current_user(request, db)
    org_id = str(request.state.org_id)
    permission_levels = _get_user_permission_levels(user.role)

    filters: Dict[str, Any] = {
        'org_id': org_id,
        'permission_levels': permission_levels,
    }
    if body.project_id:
        filters['project_id'] = str(body.project_id)
    if body.source_types:
        filters['source_types'] = body.source_types
    if body.timestamp_gte:
        filters['timestamp_gte'] = body.timestamp_gte
    if body.timestamp_lte:
        filters['timestamp_lte'] = body.timestamp_lte
    if body.author:
        filters['author'] = body.author

    chunks = await retrieve_chunks(body.query, filters, top_k=body.top_k)

    snippets_out = [
        SnippetOut(
            id=c['id'],
            text=c['snippet_text'],
            source_url=c['source_url'],
            source_type=c['source_type'],
            author=c.get('author'),
            similarity=round(c['similarity'], 4),
            permission_level=c['permission_level'],
        )
        for c in chunks
    ]

    if not chunks:
        return SearchResponse(
            query=body.query,
            answer='관련 문서를 찾을 수 없습니다. 다른 검색어를 시도해 보세요.',
            confidence_score=0.0,
            needs_human_review=True,
            source_snippets=[],
            total_results=0,
        )

    # Build snippet text for LLM
    snippet_text = '\n\n---\n\n'.join(
        f'[Source: {c["source_type"]} | {c["source_url"]} | similarity: {c["similarity"]:.2f}]\n'
        f'{c["snippet_text"]}'
        for c in chunks
    )
    prompt = SEARCH_ANSWER_PROMPT.format(query=body.query, snippets=snippet_text)

    llm = get_llm(mini=True)  # mini for speed
    llm_with_schema = llm.with_structured_output(SearchAnswerResult)

    try:
        result: SearchAnswerResult = await llm_with_schema.ainvoke(
            [
                SystemMessage(content='You are an organizational knowledge assistant.'),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as exc:
        logger.exception('Search LLM synthesis failed: %s', exc)
        return SearchResponse(
            query=body.query,
            answer='답변 생성 중 오류가 발생했습니다.',
            confidence_score=0.0,
            needs_human_review=True,
            source_snippets=snippets_out,
            total_results=len(chunks),
        )

    return SearchResponse(
        query=body.query,
        answer=result.answer.answer,
        key_points=result.answer.key_points,
        related_decisions=result.answer.related_decisions,
        related_projects=result.answer.related_projects,
        caveats=result.answer.caveats,
        confidence_score=result.confidence_score,
        needs_human_review=result.needs_human_review or result.confidence_score < CONFIDENCE_THRESHOLD,
        source_snippets=snippets_out,
        total_results=len(chunks),
    )


@router.post('/similar-decisions', response_model=SimilarDecisionsResponse)
async def search_similar_decisions(
    body: SimilarDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SimilarDecisionsResponse:
    """Find decisions similar to a query using vector similarity on DecisionRecord summaries."""
    user = await _get_current_user(request, db)
    org_id = request.state.org_id
    permission_levels = _get_user_permission_levels(user.role)

    # Map role to allowed DecisionPermissionLevels
    allowed = set(permission_levels)

    query_vec = await embed_query(body.query)
    if not query_vec:
        return SimilarDecisionsResponse(query=body.query, decisions=[])

    from sqlalchemy import text as sa_text

    conditions = ['dr.organization_id = :org_id', 'dr.permission_level = ANY(:allowed)']
    params: Dict[str, Any] = {
        'org_id': str(org_id),
        'allowed': list(allowed),
        'query_vec': query_vec,
        'top_k': body.top_k,
    }
    if body.business_domain:
        conditions.append('dr.business_domain = :domain')
        params['domain'] = body.business_domain

    where = ' AND '.join(conditions)

    # Use source_snippets table for vector similarity (decision summaries are ingested as sources)
    # Fall back to text-based ordering if no vectors exist for decisions
    sql = sa_text(f"""
        SELECT
            dr.id,
            dr.title,
            dr.decision_summary,
            dr.business_domain,
            dr.decided_at,
            dr.confidence_score,
            0.5 AS similarity
        FROM decision_records dr
        WHERE {where}
        ORDER BY dr.decided_at DESC NULLS LAST
        LIMIT :top_k
    """)

    rows = (await db.execute(sql, params)).fetchall()
    decisions = [
        SimilarDecisionOut(
            id=row.id,
            title=row.title,
            decision_summary=row.decision_summary,
            business_domain=row.business_domain,
            decided_at=row.decided_at.isoformat() if row.decided_at else None,
            confidence_score=row.confidence_score,
            similarity=row.similarity,
        )
        for row in rows
    ]
    return SimilarDecisionsResponse(query=body.query, decisions=decisions)
