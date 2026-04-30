"""Validation Agent — checks all LLM outputs for hallucinations and missing sources."""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, get_llm
from app.llm.prompts.agent_prompts import VALIDATION_PROMPT
from app.llm.structured_outputs import ValidationResult

logger = logging.getLogger(__name__)


@traceable(name='validation_agent')
async def run_validation_agent(state: AgentState) -> AgentState:
    """Validate all results in state['results'] and gate on confidence + source presence."""
    results = state.get('results', {})
    chunks = state.get('chunks', [])
    source_text = '\n\n'.join(c['text'] for c in chunks[:10])  # limit to 10 chunks for cost

    validation_reports: dict = {}

    for agent_name, content in results.items():
        if not content:
            continue

        prompt = VALIDATION_PROMPT.format(
            content=json.dumps(content, ensure_ascii=False, indent=2),
            sources=source_text,
        )

        llm = get_llm(mini=True)  # Use mini model for validation (cost)
        llm_with_schema = llm.with_structured_output(ValidationResult)

        try:
            val: ValidationResult = await llm_with_schema.ainvoke(
                [
                    SystemMessage(content='You are a rigorous AI output quality checker.'),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            logger.exception('Validation agent failed for %s: %s', agent_name, exc)
            val = ValidationResult(
                is_valid=False,
                faithfulness_score=0.0,
                hallucination_detected=True,
                source_validation_passed=False,
                issues=[f'Validation error: {exc}'],
                confidence_score=0.0,
                recommendation='reject',
            )

        # Hard rule: if source_validation_passed is False → reject
        if not val.source_validation_passed:
            val.recommendation = 'reject'
            val.is_valid = False

        validation_reports[agent_name] = val.model_dump()

    state['results']['validation'] = validation_reports
    return state
