"""Priority Agent — assigns priority scores to todos."""
from __future__ import annotations

import json
import logging
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, get_llm
from app.llm.prompts.agent_prompts import PRIORITY_DECISION_PROMPT
from app.llm.structured_outputs import PriorityDecisionResult

logger = logging.getLogger(__name__)


@traceable(name='priority_agent')
async def run_priority_agent(state: AgentState) -> AgentState:
    """Assign priority scores to todos extracted by the Todo Agent."""
    todo_result = state.get('results', {}).get('todos', {})
    todos = todo_result.get('todos', [])

    if not todos:
        state['results']['priorities'] = []
        return state

    project_context = f"Project ID: {state.get('project_id', 'unknown')}"

    llm = get_llm(mini=False)
    llm_with_schema = llm.with_structured_output(PriorityDecisionResult)

    priority_results = []
    for todo in todos:
        prompt = PRIORITY_DECISION_PROMPT.format(
            todo=json.dumps(todo, ensure_ascii=False, indent=2),
            project_context=project_context,
        )

        try:
            result: PriorityDecisionResult = await llm_with_schema.ainvoke(
                [
                    SystemMessage(content='You are a work prioritization expert.'),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            logger.exception('Priority agent failed for todo: %s', exc)
            state['errors'].append(f'priority_agent: {exc}')
            result = PriorityDecisionResult(
                priority='medium',
                priority_score=50,
                reason=f'Auto-assigned due to LLM error: {exc}',
                factors={},
                source_links=[],
                source_snippets=[],
                confidence_score=0.0,
                missing_evidence=[str(exc)],
                needs_human_review=True,
            )

        # Force human review for high-stakes items
        f = result.factors
        if f.is_blocker or f.c_level_report or f.needs_consensus:
            result.needs_human_review = True

        priority_results.append(result.model_dump())

    state['results']['priorities'] = priority_results
    return state
