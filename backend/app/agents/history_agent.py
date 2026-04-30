"""History Agent — extracts decision-making history from document chunks."""
from __future__ import annotations

import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, DocumentChunk, get_llm
from app.llm.prompts.agent_prompts import HISTORY_EXTRACTION_PROMPT
from app.llm.structured_outputs import HistoryExtractionResult

logger = logging.getLogger(__name__)


def _build_document_text(chunks: List[DocumentChunk]) -> str:
    parts = []
    for chunk in chunks:
        parts.append(
            f'[Source: {chunk["source_type"]} | URL: {chunk["source_url"]} | '
            f'Author: {chunk["author"]} | Time: {chunk["timestamp"]}]\n'
            f'{chunk["text"]}'
        )
    return '\n\n---\n\n'.join(parts)


@traceable(name='history_agent')
async def run_history_agent(state: AgentState) -> AgentState:
    """Extract HistoryEvents from chunks and store result in state['results']['history']."""
    chunks = state['chunks']
    if not chunks:
        state['results']['history'] = HistoryExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=['No source documents provided'],
        ).model_dump()
        return state

    doc_text = _build_document_text(chunks)
    prompt = HISTORY_EXTRACTION_PROMPT.format(documents=doc_text)

    llm = get_llm(mini=False)
    llm_with_schema = llm.with_structured_output(HistoryExtractionResult)

    try:
        result: HistoryExtractionResult = await llm_with_schema.ainvoke(
            [
                SystemMessage(content='You are a workplace decision-history extraction expert.'),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as exc:
        logger.exception('History agent LLM call failed: %s', exc)
        state['errors'].append(f'history_agent: {exc}')
        result = HistoryExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=[f'LLM error: {exc}'],
        )

    # Force human review if confidence too low or sources missing
    if result.confidence_score < 0.7 or not result.source_links:
        result.needs_human_review = True
        if not result.source_links:
            result.missing_evidence.append('No source_links provided')

    state['results']['history'] = result.model_dump()
    return state
