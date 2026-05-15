import json
import re
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ProjectOption(BaseModel):
    project_key: str
    name: str
    summary: str


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


def score_project_aliases(
    text: str,
    projects: list[ProjectOption],
) -> list[dict[str, Any]]:
    normalized = _normalize(text)
    ranked: list[dict[str, Any]] = []
    for project in projects:
        terms = _project_terms(project)
        hits = [term for term in terms if _contains_term(normalized, term)]
        score = min(1.0, len(hits) / max(2, len(terms)))
        ranked.append(
            {
                'project_key': project.project_key,
                'name': project.name,
                'score': round(score, 4),
                'matched_terms': hits[:8],
            }
        )
    return sorted(ranked, key=lambda item: item['score'], reverse=True)


def build_project_tools(projects: list[ProjectOption]):
    @tool
    def list_registered_projects() -> str:
        """Return registered ParaWorks projects as JSON."""
        return json.dumps(
            [project.model_dump() for project in projects],
            ensure_ascii=False,
        )

    @tool
    def score_project_candidates(text: str) -> str:
        """Return deterministic project candidate scores for evidence text."""
        return json.dumps(
            score_project_aliases(text, projects),
            ensure_ascii=False,
        )

    return [list_registered_projects, score_project_candidates]


def route_projects_for_candidates(
    *,
    model: Any,
    projects: list[ProjectOption],
    candidates: list[dict[str, Any]],
) -> ProjectRoutingResult:
    if not projects or not candidates:
        return ProjectRoutingResult(decisions=[])

    payload = {
        'task': (
            '등록 프로젝트 중 Slack 후보가 어느 프로젝트에 속하는지 고르고, '
            '프로젝트 활동 요약과 근거를 한국어로 작성하세요.'
        ),
        'rules': [
            '반드시 list_registered_projects tool로 프로젝트 목록을 확인하세요.',
            '프로젝트가 애매하면 score_project_candidates tool 결과를 참고하세요.',
            '등록 프로젝트에 해당한다고 판단한 경우에만 project_key를 채우세요.',
            '근거가 부족하면 project_key를 null로 두고 needs_user_selection=true로 두세요.',
            '새 프로젝트를 만들지 마세요. 등록된 프로젝트 중에서만 선택하세요.',
            '모든 candidate_items에 대해 decisions 항목을 하나씩 반환하세요.',
        ],
        'projects_count': len(projects),
        'candidate_items': candidates,
    }

    raw_result = model.invoke(payload)
    if isinstance(raw_result, ProjectRoutingResult):
        return raw_result
    if isinstance(raw_result, dict):
        return ProjectRoutingResult.model_validate(raw_result)
    return ProjectRoutingResult.model_validate_json(str(raw_result))


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
                '당신은 ParaWorks Slack 프로젝트 분류 Router입니다. '
                '결정하기 전에 반드시 tool을 사용하고, 한국어 요약과 근거 기반 사유만 반환하세요.'
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
    raw = f'{project.project_key} {project.name} {project.summary}'
    terms = re.findall(r'[0-9A-Za-z가-힣]{2,}', raw.lower())
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
        'summarizes',
        'sync',
        'timeline',
        '관리',
        '관련',
        '문서',
        '업무',
        '진행',
        '프로젝트',
        '활동',
    }
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        if term in stopwords or term in seen:
            continue
        seen.add(term)
        result.append(term)
    return result


def _normalize(text: str) -> str:
    return ' '.join(text.lower().split())


def _contains_term(text: str, term: str) -> bool:
    return (
        re.search(
            rf'(?<![0-9a-z가-힣]){re.escape(term)}(?![0-9a-z가-힣])',
            text,
        )
        is not None
    )
