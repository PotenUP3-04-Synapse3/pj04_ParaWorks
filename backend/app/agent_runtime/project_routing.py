import json
import re
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ProjectOption(BaseModel):
    project_key: str
    name: str
    summary: str


class ProjectRoutingCandidate(BaseModel):
    item_index: int
    source_id: str
    title: str
    summary: str
    item_type: str
    source_type: str
    source_links: list[str] = Field(default_factory=list)
    source_snippets: list[str] = Field(default_factory=list)
    evidence_text: str = ''
    confidence_score: float = Field(ge=0, le=1)


class ProjectRoutingDecision(BaseModel):
    source_id: str
    item_index: int
    project_key: str | None = None
    project_name: str | None = None
    confidence_score: float = Field(ge=0, le=1)
    assignment_summary: str
    assignment_reason: str
    alternatives: list[str] = Field(default_factory=list)
    needs_user_selection: bool = False


class ProjectRoutingResult(BaseModel):
    decisions: list[ProjectRoutingDecision] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str = 'deterministic-project-router'


class ProjectRouterModel(Protocol):
    def invoke(self, payload: dict[str, Any]) -> ProjectRoutingResult | dict[str, Any] | str:
        raise NotImplementedError


def score_project_aliases(text: str, projects: list[ProjectOption]) -> list[dict[str, Any]]:
    normalized = _normalize(text)
    ranked: list[dict[str, Any]] = []
    for project in projects:
        terms = _project_terms(project)
        hits = [term for term in terms if _contains_term(normalized, term)]
        ranked.append(
            {
                'project_key': project.project_key,
                'name': project.name,
                'score': round(min(1.0, len(hits) / max(2, len(terms))), 4),
                'matched_terms': hits[:8],
            }
        )
    return sorted(ranked, key=lambda item: item['score'], reverse=True)


def build_project_tools(projects: list[ProjectOption]) -> list[Any]:
    from langchain_core.tools import tool

    @tool
    def list_registered_projects() -> str:
        """Return registered ParaWorks projects as JSON."""
        return json.dumps([project.model_dump() for project in projects], ensure_ascii=False)

    @tool
    def score_project_candidates(text: str) -> str:
        """Return deterministic project candidate scores for evidence text."""
        return json.dumps(score_project_aliases(text, projects), ensure_ascii=False)

    return [list_registered_projects, score_project_candidates]


def route_projects_for_candidates(
    *,
    model: ProjectRouterModel,
    projects: list[ProjectOption],
    candidates: list[ProjectRoutingCandidate],
) -> ProjectRoutingResult:
    if not projects or not candidates:
        return ProjectRoutingResult(decisions=[])

    payload = {
        'task': 'Route each review candidate to one registered project, or require reviewer selection.',
        'rules': [
            'Use only registered projects from the provided project list.',
            'Return one decision for every candidate item.',
            'If evidence is insufficient, leave project_key null and set needs_user_selection true.',
            'Do not create a new project key.',
        ],
        'projects_count': len(projects),
        'projects': [project.model_dump() for project in projects],
        'candidate_items': [candidate.model_dump() for candidate in candidates],
    }

    raw_result = model.invoke(payload)
    if isinstance(raw_result, ProjectRoutingResult):
        return raw_result
    if isinstance(raw_result, dict):
        return ProjectRoutingResult.model_validate(raw_result)
    return ProjectRoutingResult.model_validate_json(str(raw_result))


def apply_project_routing_to_payload(
    payload: dict[str, Any],
    decision: ProjectRoutingDecision,
) -> dict[str, Any]:
    updated = dict(payload)
    updated.update(
        {
            'project_assignment_method': 'llm_tool',
            'project_assignment_summary': decision.assignment_summary,
            'project_assignment_reason': decision.assignment_reason,
            'project_assignment_confidence': decision.confidence_score,
            'project_alternatives': decision.alternatives,
            'project_needs_user_selection': decision.needs_user_selection,
        }
    )
    if decision.project_key:
        updated['project_key'] = decision.project_key
    else:
        updated.pop('project_key', None)
    if decision.project_name:
        updated['project_name'] = decision.project_name
    else:
        updated.pop('project_name', None)
    return updated


class LangChainProjectRouterModel:
    def __init__(
        self,
        *,
        chat_model: Any,
        projects: list[ProjectOption],
        model_name: str,
    ) -> None:
        from langchain.agents import create_agent

        self.model_name = model_name
        self.agent = create_agent(
            model=chat_model,
            tools=build_project_tools(projects),
            response_format=ProjectRoutingResult,
            system_prompt=(
                'You are the ParaWorks project routing agent. Use tools before deciding, '
                'preserve uncertainty, and return concise reviewer-facing reasons.'
            ),
        )

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.agent.invoke(
            {
                'messages': [
                    {
                        'role': 'user',
                        'content': json.dumps(payload, ensure_ascii=False),
                    }
                ]
            }
        )
        structured = response.get('structured_response')
        if isinstance(structured, ProjectRoutingResult):
            return structured.model_dump()
        return ProjectRoutingResult.model_validate(structured).model_dump()


def _project_terms(project: ProjectOption) -> list[str]:
    raw = f'{project.project_key} {project.name} {project.summary}'.lower()
    terms = re.findall(r'[0-9A-Za-z가-힣]{2,}', raw)
    stopwords = {
        'data',
        'drive',
        'file',
        'files',
        'gmail',
        'google',
        'project',
        'slack',
        'source',
        'sources',
        'sync',
        'timeline',
        '문서',
        '업무',
        '진행',
        '프로젝트',
        '활동',
    }
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in stopwords or term in seen:
            continue
        seen.add(term)
        result.append(term)
    return result


def _normalize(text: str) -> str:
    return ' '.join(text.lower().split())


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf'(?<![0-9a-z가-힣]){re.escape(term)}(?![0-9a-z가-힣])', text) is not None
