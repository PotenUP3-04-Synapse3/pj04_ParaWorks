"""Decision Record Agent — extracts formal organizational decisions from document chunks."""
from __future__ import annotations

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, DocumentChunk, get_llm
from app.llm.prompts.agent_prompts import DECISION_RECORD_EXTRACTION_PROMPT
from app.llm.structured_outputs import DecisionRecordExtractionResult

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


@traceable(name='decision_record_agent')
async def run_decision_record_agent(state: AgentState) -> AgentState:
    """Extract DecisionRecords from chunks and store result in state['results']['decisions']."""
    chunks = state['chunks']
    if not chunks:
        state['results']['decisions'] = DecisionRecordExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=['No source documents provided'],
        ).model_dump()
        return state

    doc_text = _build_document_text(chunks)
    prompt = DECISION_RECORD_EXTRACTION_PROMPT.format(documents=doc_text)

    llm = get_llm(mini=False)
    llm_with_schema = llm.with_structured_output(DecisionRecordExtractionResult)

    try:
        result: DecisionRecordExtractionResult = await llm_with_schema.ainvoke(
            [
                SystemMessage(
                    content=(
                        'You are an expert at identifying and structuring formal organizational '
                        'decisions from workplace communications. Be conservative — only extract '
                        'genuine strategic decisions with clear evidence.'
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as exc:
        logger.exception('Decision record agent LLM call failed: %s', exc)
        state['errors'].append(f'decision_record_agent: {exc}')
        result = DecisionRecordExtractionResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=[f'LLM error: {exc}'],
        )

    # Enforce human review for low-confidence results
    if result.confidence_score < 0.7 or result.missing_evidence:
        result.needs_human_review = True

    state['results']['decisions'] = result.model_dump()
    return state
