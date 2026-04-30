"""Todo Agent — extracts actionable tasks from document chunks."""
from __future__ import annotations

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, DocumentChunk, get_llm
from app.llm.prompts.agent_prompts import TODO_EXTRACTION_PROMPT
from app.llm.structured_outputs import TodoExtractionResult

logger = logging.getLogger(__name__)


def _build_document_text(chunks: List[DocumentChunk]) -> str:
    parts = []
    for chunk in chunks:
        parts.append(
            f'[Source: {chunk["source_type"]} | URL: {chunk["source_url"]} | '
            f'Author: {chunk["author"]} | Time: {chunk["timestamp"]}]\n{chunk["text"]}'
        )
    return '\n\n---\n\n'.join(parts)


@traceable(name='todo_agent')
async def run_todo_agent(state: AgentState) -> AgentState:
    chunks = state['chunks']
    if not chunks:
        state['results']['todos'] = TodoExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=['No source documents provided'],
        ).model_dump()
        return state

    llm = get_llm(mini=False)
    llm_with_schema = llm.with_structured_output(TodoExtractionResult)
    prompt = TODO_EXTRACTION_PROMPT.format(documents=_build_document_text(chunks))

    try:
        result: TodoExtractionResult = await llm_with_schema.ainvoke(
            [
                SystemMessage(content='You are an expert at extracting actionable tasks.'),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as exc:
        logger.exception('Todo agent LLM call failed: %s', exc)
        state['errors'].append(f'todo_agent: {exc}')
        result = TodoExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=[f'LLM error: {exc}'],
        )

    if result.confidence_score < 0.7 or not result.source_links:
        result.needs_human_review = True

    state['results']['todos'] = result.model_dump()
    return state
