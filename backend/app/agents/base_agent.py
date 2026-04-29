"""Base agent — shared LangGraph state and LLM client."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from app.core.config import settings


class DocumentChunk(TypedDict):
    """Standardized unit produced by the Parser Agent."""
    source_type: str          # gmail | slack | google_drive | github | calendar
    source_id: str            # external message/doc ID
    source_url: str
    project_id: Optional[str]
    campaign_id: Optional[str]
    author: str
    participants: List[str]
    timestamp: str            # ISO8601
    channel: Optional[str]
    thread_id: Optional[str]
    document_version: Optional[str]
    permission_level: str     # public | team | restricted
    tags: List[str]
    chunk_index: int
    total_chunks: int
    text: str                 # actual content


class AgentState(TypedDict):
    """Shared state passed between nodes in a LangGraph pipeline."""
    chunks: List[DocumentChunk]
    project_id: Optional[str]
    org_id: str
    results: Dict[str, Any]
    errors: List[str]


def get_llm(mini: bool = False) -> ChatOpenAI:
    model = settings.OPENAI_MINI_MODEL if mini else settings.OPENAI_MODEL
    return ChatOpenAI(
        model=model,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
