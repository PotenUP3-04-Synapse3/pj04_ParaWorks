from __future__ import annotations

"""검색 에이전트 — LangChain 1.2 create_agent + ProviderStrategy(SearchResponse, strict=True).

구조화된 응답(8 fields): answer, related_timeline, related_history,
related_decision_records, source_links, source_snippets, confidence_score,
missing_evidence, permission_notice
"""

import json
import uuid
from typing import Any

import structlog
from langchain.agents import create_agent, AgentState  # type: ignore
from langchain.agents.structured_output import ProviderStrategy  # type: ignore
from langchain.tools import tool  # type: ignore
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.indexer import VectorStore
from backend.schemas.search import SearchResponse
from backend.agents.middleware import (
    ToolCallLoggingMiddleware,
    tool_call_logger,
    model_retry_middleware,
    ContentModerationMiddleware,
    permission_check_middleware,
)

log = structlog.get_logger(__name__)

_vector_store = VectorStore()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
async def hybrid_search(query: str, org_id: str, top_k: int = 10) -> str:
    """벡터 유사도 + 키워드 검색으로 관련 문서 청크를 반환합니다."""
    from backend.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        results = await _vector_store.similarity_search(
            session=session,
            query=query,
            organization_id=org_id,
            top_k=top_k,
        )
    return json.dumps(results, ensure_ascii=False)


@tool
async def get_decision_records(org_id: str, keywords: str, limit: int = 5) -> str:
    """의사결정 레코드에서 키워드 기반 검색을 수행합니다."""
    from backend.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, title, decision_summary, context, rationale, decided_at, "
                "       confidence_score "
                "FROM decision_records "
                "WHERE organization_id = :org_id "
                "  AND (title ILIKE :kw OR decision_summary ILIKE :kw) "
                "ORDER BY decided_at DESC LIMIT :lim"
            ),
            {'org_id': org_id, 'kw': f'%{keywords}%', 'lim': limit},
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
    return json.dumps(rows, ensure_ascii=False, default=str)


@tool
async def get_timeline_events(org_id: str, query: str, limit: int = 8) -> str:
    """조직 타임라인에서 관련 이벤트를 검색합니다 (문서, 의사결정, 캘린더)."""
    from backend.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT dc.id, dc.title, dc.source_type, dc.source_url, dv.created_at "
                "FROM document_collections dc "
                "JOIN document_versions dv ON dv.collection_id = dc.id "
                "WHERE dc.organization_id = :org_id "
                "  AND dc.title ILIKE :kw "
                "ORDER BY dv.created_at DESC LIMIT :lim"
            ),
            {'org_id': org_id, 'kw': f'%{query}%', 'lim': limit},
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
    return json.dumps(rows, ensure_ascii=False, default=str)


@tool
async def get_knowledge_assets(org_id: str, query: str, limit: int = 5) -> str:
    """지식 자산(암묵지/형식지) 검색."""
    from backend.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, title, asset_type, summary, tags "
                "FROM knowledge_assets "
                "WHERE organization_id = :org_id "
                "  AND (title ILIKE :kw OR summary ILIKE :kw) "
                "ORDER BY updated_at DESC LIMIT :lim"
            ),
            {'org_id': org_id, 'kw': f'%{query}%', 'lim': limit},
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
    return json.dumps(rows, ensure_ascii=False, default=str)


_TOOLS = [hybrid_search, get_decision_records, get_timeline_events, get_knowledge_assets]

_SYSTEM_PROMPT = """\
당신은 전사 지식 관리 AI 어시스턴트입니다.
사용자의 질문에 대해 조직 내 문서, 의사결정 기록, 타임라인을 검색하여 정확하고 투명한 답변을 제공합니다.

규칙:
1. 반드시 제공된 tool을 사용하여 실제 데이터를 검색하세요.
2. 개인정보(주민번호, 연락처, 카드번호)는 절대 노출하지 마세요.
3. 불확실한 내용은 missing_evidence에 명시하세요.
4. 응답은 SearchResponse 형식으로만 반환하세요.
5. confidence_score는 0.0~1.0 범위의 숫자입니다.
"""


def build_search_agent(checkpointer: Any | None = None):
    """검색 에이전트 인스턴스를 빌드하여 반환."""
    agent = create_agent(
        model=f"azure:{settings.azure_openai_deployment_chat}",
        tools=_TOOLS,
        response_format=ProviderStrategy(SearchResponse, strict=True),
        middleware=[
            ToolCallLoggingMiddleware(),
            model_retry_middleware,
            ContentModerationMiddleware(),
            permission_check_middleware,
        ],
        checkpointer=checkpointer,
        system_prompt=_SYSTEM_PROMPT,
    )
    return agent


async def search(
    query: str,
    organization_id: str,
    user_id: str,
    accessible_permission_levels: list[str],
    thread_id: str | None = None,
) -> SearchResponse:
    """외부에서 호출하는 진입점. 검색 에이전트를 실행하고 SearchResponse를 반환."""
    agent = build_search_agent()
    config = {
        'configurable': {
            'thread_id': thread_id or str(uuid.uuid4()),
        }
    }
    initial_state: AgentState = {
        'messages': [{'role': 'user', 'content': query}],
        'org_id': organization_id,
        'user_id': user_id,
        'accessible_permission_levels': accessible_permission_levels,
    }
    result = await agent.ainvoke(initial_state, config=config, version='v2')
    return result.structured_output
