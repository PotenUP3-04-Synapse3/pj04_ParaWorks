"""RAG Retrieval Agent — semantic search over pgvector with metadata filters."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, get_llm
from app.rag.retriever import retrieve_chunks

logger = logging.getLogger(__name__)

_SELF_QUERY_PROMPT = """
You are a search query parser. Convert the natural language query into a structured filter.

User query: {query}

Return a JSON object with these optional fields:
- keywords: [string] - main search terms
- source_types: [gmail|slack|google_drive|github|calendar]
- project_id: string or null
- author: string or null
- timestamp_gte: ISO8601 string or null (from date)
- timestamp_lte: ISO8601 string or null (to date)
- permission_levels: [public|team|restricted]

Example:
Query: "지난주 결제 오류 관련 의사결정 찾아줘"
Result: {{"keywords": ["결제", "오류", "의사결정"], "timestamp_gte": "2026-04-21T00:00:00Z", "source_types": ["slack", "gmail"]}}

Return ONLY valid JSON, no markdown.
"""


@traceable(name='rag_retrieval_agent')
async def run_rag_retrieval_agent(
    query: str,
    org_id: str,
    user_permission_levels: List[str],
    project_id: Optional[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Convert natural language query to structured filter and retrieve relevant chunks."""
    # Self-querying: parse query into filters
    llm = get_llm(mini=True)
    prompt = _SELF_QUERY_PROMPT.format(query=query)

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content='Parse the search query into structured filters.'),
                HumanMessage(content=prompt),
            ]
        )
        filters = json.loads(response.content)
    except Exception as exc:
        logger.warning('Self-query parsing failed, using raw query: %s', exc)
        filters = {'keywords': [query]}

    # Inject security filters — never skip
    filters['org_id'] = org_id
    filters['permission_levels'] = user_permission_levels
    if project_id:
        filters['project_id'] = project_id

    return await retrieve_chunks(query=query, filters=filters, top_k=top_k)
