from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Protocol

from backend.app.agent_runtime import EvidencePacket, ReviewCandidate

PROJECT_OPTIONS_CONTEXT_KEY = 'project_options'
PROJECT_ROUTER_CONTEXT_KEY = 'project_router'
PROJECT_ROUTING_CONTEXT_KEY = 'project_routing'


@dataclass(frozen=True)
class MailDocumentProjectOption:
    project_key: str
    name: str
    summary: str


@dataclass(frozen=True)
class MailDocumentProjectRoutingCandidate:
    item_index: int
    source_id: str
    title: str
    summary: str
    item_type: str
    source_type: str
    source_links: list[str]
    source_snippets: list[str]
    evidence_text: str
    confidence_score: float


@dataclass(frozen=True)
class MailDocumentProjectRoutingDecision:
    source_id: str
    item_index: int
    project_key: str | None
    project_name: str | None
    confidence_score: float
    assignment_summary: str
    assignment_reason: str
    alternatives: list[str]
    needs_user_selection: bool


@dataclass(frozen=True)
class MailDocumentProjectRoutingResult:
    decisions: list[MailDocumentProjectRoutingDecision]
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str = 'deterministic-mail-document-project-router'


class MailDocumentProjectRouter(Protocol):
    def route(
        self,
        *,
        candidates: list[MailDocumentProjectRoutingCandidate],
        projects: list[Any],
    ) -> MailDocumentProjectRoutingResult | dict[str, Any]:
        raise NotImplementedError


class DeterministicMailDocumentProjectRouter:
    model_name = 'deterministic-mail-document-project-router'

    def route(
        self,
        *,
        candidates: list[MailDocumentProjectRoutingCandidate],
        projects: list[Any],
    ) -> MailDocumentProjectRoutingResult:
        decisions: list[MailDocumentProjectRoutingDecision] = []
        for candidate in candidates:
            project = _best_project_match(candidate, projects)
            if project is None:
                decisions.append(
                    MailDocumentProjectRoutingDecision(
                        source_id=candidate.source_id,
                        item_index=candidate.item_index,
                        project_key=None,
                        project_name=None,
                        confidence_score=0.35,
                        assignment_summary='등록 프로젝트와 확정 매칭되지 않습니다.',
                        assignment_reason='후보의 제목, 요약, 증거 문구가 등록 프로젝트 설명과 충분히 일치하지 않습니다.',
                        alternatives=[str(_project_field(option, 'project_key')) for option in projects[:3]],
                        needs_user_selection=True,
                    )
                )
                continue
            decisions.append(
                MailDocumentProjectRoutingDecision(
                    source_id=candidate.source_id,
                    item_index=candidate.item_index,
                    project_key=str(_project_field(project, 'project_key')),
                    project_name=str(_project_field(project, 'name')),
                    confidence_score=0.82,
                    assignment_summary=f"{candidate.title} 후보가 {_project_field(project, 'name')} 프로젝트와 연결됩니다.",
                    assignment_reason='후보의 제목, 요약, 증거 문구가 등록 프로젝트의 이름 또는 설명과 일치합니다.',
                    alternatives=[
                        str(_project_field(option, 'project_key'))
                        for option in projects
                        if _project_field(option, 'project_key') != _project_field(project, 'project_key')
                    ][:3],
                    needs_user_selection=False,
                )
            )
        return MailDocumentProjectRoutingResult(
            decisions=decisions,
            input_tokens=sum(max(1, len(candidate.evidence_text) // 4) for candidate in candidates),
            output_tokens=max(0, len(decisions) * 48),
            model_name=self.model_name,
        )


def route_candidates_from_packet(
    *,
    candidates: list[ReviewCandidate],
    packet: EvidencePacket,
) -> tuple[list[ReviewCandidate], MailDocumentProjectRoutingResult]:
    projects = _context_projects(packet)
    router = _context_router(packet)
    if not projects or not candidates:
        result = MailDocumentProjectRoutingResult(
            decisions=[],
            model_name=getattr(router, 'model_name', 'deterministic-mail-document-project-router'),
        )
        packet.context[PROJECT_ROUTING_CONTEXT_KEY] = _routing_metadata(
            result=result,
            project_count=len(projects),
        )
        return candidates, result

    result = project_route_mail_document_candidates(
        candidates=candidates,
        packet=packet,
        projects=projects,
        router_model=router,
    )
    routed = _apply_project_routing_to_candidates(candidates=candidates, decisions=result.decisions)
    packet.context[PROJECT_ROUTING_CONTEXT_KEY] = _routing_metadata(
        result=result,
        project_count=len(projects),
    )
    return routed, result


def project_route_mail_document_candidates(
    *,
    candidates: list[ReviewCandidate],
    packet: EvidencePacket,
    projects: list[Any],
    router_model: MailDocumentProjectRouter,
) -> MailDocumentProjectRoutingResult:
    source_id = '|'.join(_unique_strings(message.source_id for message in packet.messages))
    routing_candidates = [
        MailDocumentProjectRoutingCandidate(
            item_index=index,
            source_id=source_id,
            title=candidate.title,
            summary=candidate.summary,
            item_type=candidate.item_type,
            source_type=packet.source_type,
            source_links=_unique_strings(candidate.source_links),
            source_snippets=_unique_strings(candidate.source_snippets),
            evidence_text='\n'.join(_unique_strings(candidate.source_snippets)[:3]),
            confidence_score=candidate.confidence_score,
        )
        for index, candidate in enumerate(candidates)
    ]
    return _coerce_project_routing_result(router_model.route(candidates=routing_candidates, projects=projects))


def _context_projects(packet: EvidencePacket) -> list[Any]:
    projects = packet.context.get(PROJECT_OPTIONS_CONTEXT_KEY)
    return projects if isinstance(projects, list) else []


def _context_router(packet: EvidencePacket) -> MailDocumentProjectRouter:
    router = packet.context.get(PROJECT_ROUTER_CONTEXT_KEY)
    if router is not None and hasattr(router, 'route'):
        return router
    return DeterministicMailDocumentProjectRouter()


def _routing_metadata(
    *,
    result: MailDocumentProjectRoutingResult,
    project_count: int,
) -> dict[str, object]:
    return {
        'enabled': project_count > 0,
        'method': 'langchain_tools',
        'project_count': project_count,
        'model_name': result.model_name,
        'input_tokens': result.input_tokens,
        'output_tokens': result.output_tokens,
    }


def _apply_project_routing_to_candidates(
    *,
    candidates: list[ReviewCandidate],
    decisions: list[MailDocumentProjectRoutingDecision],
) -> list[ReviewCandidate]:
    decisions_by_index = {decision.item_index: decision for decision in decisions}
    routed: list[ReviewCandidate] = []
    for index, candidate in enumerate(candidates):
        decision = decisions_by_index.get(index)
        if decision is None:
            routed.append(candidate)
            continue
        routed.append(_apply_project_routing_to_candidate(candidate, decision))
    return routed


def _apply_project_routing_to_candidate(
    candidate: ReviewCandidate,
    decision: MailDocumentProjectRoutingDecision,
) -> ReviewCandidate:
    payload_fields = {
        **candidate.payload_fields,
        'project_assignment_method': 'llm_tool',
        'project_assignment_summary': decision.assignment_summary,
        'project_assignment_reason': decision.assignment_reason,
        'project_assignment_confidence': decision.confidence_score,
        'project_alternatives': decision.alternatives,
        'project_needs_user_selection': decision.needs_user_selection,
    }
    if decision.project_key:
        payload_fields['project_key'] = decision.project_key
    if decision.project_name:
        payload_fields['project_name'] = decision.project_name
    return replace(candidate, payload_fields=payload_fields)


def _coerce_project_routing_result(
    raw_result: MailDocumentProjectRoutingResult | dict[str, Any],
) -> MailDocumentProjectRoutingResult:
    if isinstance(raw_result, MailDocumentProjectRoutingResult):
        return raw_result
    if not isinstance(raw_result, dict):
        return MailDocumentProjectRoutingResult(decisions=[])
    return MailDocumentProjectRoutingResult(
        decisions=[
            _coerce_project_routing_decision(decision)
            for decision in raw_result.get('decisions', [])
            if isinstance(decision, dict)
        ],
        input_tokens=int(raw_result.get('input_tokens') or 0),
        output_tokens=int(raw_result.get('output_tokens') or 0),
        model_name=str(raw_result.get('model_name') or 'deterministic-mail-document-project-router'),
    )


def _coerce_project_routing_decision(raw_decision: dict[str, Any]) -> MailDocumentProjectRoutingDecision:
    return MailDocumentProjectRoutingDecision(
        source_id=str(raw_decision.get('source_id') or ''),
        item_index=int(raw_decision.get('item_index') or 0),
        project_key=_optional_string(raw_decision.get('project_key')),
        project_name=_optional_string(raw_decision.get('project_name')),
        confidence_score=_clamped_float(raw_decision.get('confidence_score'), default=0.0),
        assignment_summary=str(raw_decision.get('assignment_summary') or '등록 프로젝트와 확정 매칭되지 않습니다.'),
        assignment_reason=str(raw_decision.get('assignment_reason') or '프로젝트 라우팅 근거가 충분하지 않습니다.'),
        alternatives=[
            str(value)
            for value in raw_decision.get('alternatives', [])
            if isinstance(value, str) and value.strip()
        ],
        needs_user_selection=bool(raw_decision.get('needs_user_selection')),
    )


def _best_project_match(
    candidate: MailDocumentProjectRoutingCandidate,
    projects: list[Any],
) -> Any | None:
    haystack = ' '.join(
        [
            candidate.source_id,
            candidate.title,
            candidate.summary,
            candidate.evidence_text,
            *candidate.source_links,
        ]
    ).lower()
    for project in projects:
        terms = _project_match_terms(project)
        if any(term and term in haystack for term in terms):
            return project
    return None


def _project_match_terms(project: Any) -> list[str]:
    terms = {
        str(_project_field(project, 'project_key')).lower(),
        str(_project_field(project, 'name')).lower(),
        str(_project_field(project, 'name')).lower().replace(' ', '-'),
        str(_project_field(project, 'name')).lower().replace(' ', ''),
    }
    for token in str(_project_field(project, 'summary')).lower().replace(',', ' ').replace('.', ' ').split():
        if len(token) >= 4:
            terms.add(token)
    return sorted(terms, key=len, reverse=True)


def _project_field(project: Any, field_name: str) -> Any:
    if isinstance(project, dict):
        return project.get(field_name, '')
    return getattr(project, field_name, '')


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _clamped_float(value: Any, *, default: float) -> float:
    try:
        return min(max(float(value), 0.0), 1.0)
    except (TypeError, ValueError):
        return default


def _unique_strings(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
