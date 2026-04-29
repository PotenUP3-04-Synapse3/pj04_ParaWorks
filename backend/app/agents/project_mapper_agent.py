"""Project Mapper Agent — maps document chunks to existing projects or creates candidates."""
from __future__ import annotations

import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.agents.base_agent import AgentState, DocumentChunk, get_llm
from app.llm.prompts.agent_prompts import PROJECT_MAPPING_PROMPT
from app.llm.structured_outputs import ProjectMappingResult

logger = logging.getLogger(__name__)


@traceable(name='project_mapper_agent')
async def run_project_mapper_agent(
    state: AgentState,
    existing_projects: List[dict],
) -> AgentState:
    """Map chunks to an existing project or create a new project candidate."""
    chunks = state['chunks']
    doc_text = '\n\n---\n\n'.join(
        f'[{c["source_type"]} | {c["source_url"]} | {c["timestamp"]}]\n{c["text"]}'
        for c in chunks
    )

    llm = get_llm(mini=False)
    llm_with_schema = llm.with_structured_output(ProjectMappingResult)
    prompt = PROJECT_MAPPING_PROMPT.format(
        existing_projects=json.dumps(existing_projects, ensure_ascii=False, indent=2),
        documents=doc_text,
    )

    try:
        result: ProjectMappingResult = await llm_with_schema.ainvoke(
            [
                SystemMessage(content='You are a project organization expert.'),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as exc:
        logger.exception('Project mapper agent failed: %s', exc)
        state['errors'].append(f'project_mapper_agent: {exc}')
        result = ProjectMappingResult(
            confidence_score=0.0,
            needs_human_review=True,
            missing_evidence=[f'LLM error: {exc}'],
        )

    # Auto-create candidate only needs human review; never auto-confirm
    if result.new_project_candidate is not None:
        result.needs_human_review = True

    # Low match confidence → don't auto-assign
    if result.matched_project_id and result.match_confidence < 0.75:
        result.matched_project_id = None
        result.new_project_candidate = result.new_project_candidate or None
        result.needs_human_review = True

    state['results']['project_mapping'] = result.model_dump()
    if result.matched_project_id:
        state['project_id'] = result.matched_project_id

    return state
