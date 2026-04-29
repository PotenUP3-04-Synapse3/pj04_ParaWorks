"""Timeline Agent — extracts result-oriented timeline events."""
from __future__ import annotations

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, DocumentChunk, get_llm
from app.llm.prompts.agent_prompts import TIMELINE_EXTRACTION_PROMPT
from app.llm.structured_outputs import TimelineExtractionResult

logger = logging.getLogger(__name__)


def _build_document_text(chunks: List[DocumentChunk]) -> str:
    parts = []
    for chunk in chunks:
        parts.append(
            f'[Source: {chunk["source_type"]} | URL: {chunk["source_url"]} | '
            f'Time: {chunk["timestamp"]}]\n{chunk["text"]}'
        )
    return '\n\n---\n\n'.join(parts)


@traceable(name='timeline_agent')
async def run_timeline_agent(state: AgentState) -> AgentState:
    chunks = state['chunks']
    if not chunks:
        state['results']['timeline'] = TimelineExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=['No source documents provided'],
        ).model_dump()
        return state

    llm = get_llm(mini=False)
    llm_with_schema = llm.with_structured_output(TimelineExtractionResult)
    prompt = TIMELINE_EXTRACTION_PROMPT.format(documents=_build_document_text(chunks))

    try:
        result: TimelineExtractionResult = await llm_with_schema.ainvoke(
            [
                SystemMessage(content='You are a project timeline extraction expert.'),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as exc:
        logger.exception('Timeline agent LLM call failed: %s', exc)
        state['errors'].append(f'timeline_agent: {exc}')
        result = TimelineExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=[f'LLM error: {exc}'],
        )

    if result.confidence_score < 0.7 or not result.source_links:
        result.needs_human_review = True

    state['results']['timeline'] = result.model_dump()
    return state
