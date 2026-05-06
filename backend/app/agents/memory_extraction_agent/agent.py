from dataclasses import dataclass
from typing import Protocol

from backend.app.agent_runtime import (
    AgentManifest,
    AgentRunResult,
    EvidencePacket,
    ReviewCandidate,
    TokenUsage,
    build_evidence_cache_key,
    estimate_agent_run_cost,
)

MEMORY_EXTRACTION_MODEL_NAME = 'fake-memory-extraction-model'

TIMELINE_AGENT_NAME = 'timeline_agent'
TIMELINE_AGENT_PROMPT_VERSION = 'timeline-extraction:v1'
HISTORY_AGENT_NAME = 'history_agent'
HISTORY_AGENT_PROMPT_VERSION = 'history-extraction:v1'
DECISION_RECORD_AGENT_NAME = 'decision_record_agent'
DECISION_RECORD_AGENT_PROMPT_VERSION = 'decision-record-extraction:v1'
TODO_AGENT_NAME = 'todo_agent'
TODO_AGENT_PROMPT_VERSION = 'todo-extraction:v1'

TIMELINE_AGENT_MANIFEST = AgentManifest(
    name=TIMELINE_AGENT_NAME,
    owner='Developer C',
    input_contract='EvidencePacket',
    output_contract='AgentRunResult',
    prompt_versions=(TIMELINE_AGENT_PROMPT_VERSION,),
    supported_permissions=('internal', 'restricted'),
    capabilities=('timeline_extraction',),
)
HISTORY_AGENT_MANIFEST = AgentManifest(
    name=HISTORY_AGENT_NAME,
    owner='Developer C',
    input_contract='EvidencePacket',
    output_contract='AgentRunResult',
    prompt_versions=(HISTORY_AGENT_PROMPT_VERSION,),
    supported_permissions=('internal', 'restricted'),
    capabilities=('history_generation',),
)
DECISION_RECORD_AGENT_MANIFEST = AgentManifest(
    name=DECISION_RECORD_AGENT_NAME,
    owner='Developer C',
    input_contract='EvidencePacket',
    output_contract='AgentRunResult',
    prompt_versions=(DECISION_RECORD_AGENT_PROMPT_VERSION,),
    supported_permissions=('internal', 'restricted'),
    capabilities=('decision_extraction',),
)
TODO_AGENT_MANIFEST = AgentManifest(
    name=TODO_AGENT_NAME,
    owner='Developer C',
    input_contract='EvidencePacket',
    output_contract='AgentRunResult',
    prompt_versions=(TODO_AGENT_PROMPT_VERSION,),
    supported_permissions=('internal', 'restricted'),
    capabilities=('todo_extraction',),
)


@dataclass(frozen=True)
class MemoryExtractionModelResponse:
    title: str
    summary: str
    item_type: str
    confidence_score: float
    input_tokens: int
    output_tokens: int
    payload_fields: dict[str, str]
    uncertainty_reason: str | None = None


class MemoryExtractionModel(Protocol):
    def extract(self, packet: EvidencePacket) -> MemoryExtractionModelResponse:
        raise NotImplementedError


class DeterministicTimelineModel:
    def extract(self, packet: EvidencePacket) -> MemoryExtractionModelResponse:
        combined_text = _combined_text(packet)
        summary = _first_sentence(combined_text) or '업무 결과가 발생했습니다.'
        if 'QA' in combined_text or '배포' in combined_text:
            title = 'QA and deployment milestone captured'
            summary = 'QA 완료 및 배포 진행 내역이 timeline 후보로 감지되었습니다.'
        else:
            title = 'Company timeline candidate'
        return _response(
            packet=packet,
            item_type='timeline_event',
            title=title,
            summary=summary,
            payload_fields={'result_summary': summary},
            confidence_score=0.78,
        )


class DeterministicHistoryModel:
    def extract(self, packet: EvidencePacket) -> MemoryExtractionModelResponse:
        combined_text = _combined_text(packet)
        reason = '관련 evidence를 바탕으로 업무 맥락과 이유를 검토해야 합니다.'
        title = 'Company history candidate'
        if '이유' in combined_text or 'because' in combined_text.lower():
            title = 'Business reason history captured'
            reason = '고객 데모 일정 또는 업무 제약 때문에 실행 과정이 변경된 것으로 보입니다.'
        return _response(
            packet=packet,
            item_type='history_event',
            title=title,
            summary=reason,
            payload_fields={'reason': reason},
            confidence_score=0.79,
        )


class DeterministicDecisionRecordModel:
    def extract(self, packet: EvidencePacket) -> MemoryExtractionModelResponse:
        combined_text = _combined_text(packet)
        title = 'Decision record candidate'
        decision_summary = _first_sentence(combined_text) or '의사결정 후보가 감지되었습니다.'
        if 'Redis' in combined_text and 'PostgreSQL' in combined_text:
            title = 'Redis and PostgreSQL responsibility decision'
            decision_summary = 'Redis는 작업 상태 공유에 사용하고 PostgreSQL은 영구 기록 저장소로 유지하는 결정 후보입니다.'
        elif '결정' in combined_text:
            title = 'Explicit decision cue captured'
        return _response(
            packet=packet,
            item_type='decision_record',
            title=title,
            summary=decision_summary,
            payload_fields={'decision_summary': decision_summary},
            confidence_score=0.84,
        )


class DeterministicTodoModel:
    def extract(self, packet: EvidencePacket) -> MemoryExtractionModelResponse:
        combined_text = _combined_text(packet)
        title = 'Follow-up todo candidate'
        priority = 'medium'
        priority_reason = '후속 확인이 필요한 업무 항목입니다.'
        if 'TODO' in combined_text or '권한' in combined_text or '런칭' in combined_text:
            title = 'Verify launch permission readiness'
            priority = 'high'
            priority_reason = '런칭 전 OAuth/권한 검증은 제품 신뢰성과 보안에 직접 영향을 줍니다.'
        return _response(
            packet=packet,
            item_type='todo',
            title=title,
            summary=priority_reason,
            payload_fields={'priority': priority, 'priority_reason': priority_reason},
            confidence_score=0.82,
        )


@dataclass(frozen=True)
class _MemoryExtractionAgent:
    agent_name: str
    prompt_version: str
    model: MemoryExtractionModel
    input_cost_per_1m: float = 0.15
    output_cost_per_1m: float = 0.60

    def run(self, packet: EvidencePacket) -> AgentRunResult:
        model_response = self.model.extract(packet)
        candidate = ReviewCandidate(
            item_type=model_response.item_type,
            title=model_response.title,
            summary=model_response.summary,
            source_links=packet.source_links,
            source_snippets=packet.source_snippets,
            confidence_score=model_response.confidence_score,
            permission_level=packet.strictest_permission,
            uncertainty_reason=model_response.uncertainty_reason,
            payload_fields=model_response.payload_fields,
        )
        candidate.validate_evidence()
        token_usage = TokenUsage(
            input_tokens=model_response.input_tokens,
            output_tokens=model_response.output_tokens,
        )
        cost = estimate_agent_run_cost(
            model_name=MEMORY_EXTRACTION_MODEL_NAME,
            token_usage=token_usage,
            input_cost_per_1m=self.input_cost_per_1m,
            output_cost_per_1m=self.output_cost_per_1m,
            cache_hit=False,
        )
        return AgentRunResult(
            agent_name=self.agent_name,
            prompt_version=self.prompt_version,
            candidates=[candidate],
            cost=cost,
            cache_key=build_evidence_cache_key(packet, self.prompt_version),
        )


class TimelineAgent(_MemoryExtractionAgent):
    def __init__(self, model: MemoryExtractionModel) -> None:
        super().__init__(TIMELINE_AGENT_NAME, TIMELINE_AGENT_PROMPT_VERSION, model)


class HistoryAgent(_MemoryExtractionAgent):
    def __init__(self, model: MemoryExtractionModel) -> None:
        super().__init__(HISTORY_AGENT_NAME, HISTORY_AGENT_PROMPT_VERSION, model)


class DecisionRecordAgent(_MemoryExtractionAgent):
    def __init__(self, model: MemoryExtractionModel) -> None:
        super().__init__(DECISION_RECORD_AGENT_NAME, DECISION_RECORD_AGENT_PROMPT_VERSION, model)


class TodoAgent(_MemoryExtractionAgent):
    def __init__(self, model: MemoryExtractionModel) -> None:
        super().__init__(TODO_AGENT_NAME, TODO_AGENT_PROMPT_VERSION, model)


@dataclass(frozen=True)
class ValidationAgent:
    min_confidence: float = 0.7

    def accept(self, candidate: ReviewCandidate) -> bool:
        try:
            candidate.validate_evidence()
        except ValueError:
            return False
        if candidate.confidence_score < self.min_confidence:
            return False
        if candidate.item_type == 'decision_record':
            return bool(candidate.payload_fields.get('decision_summary') or candidate.summary)
        if candidate.item_type == 'timeline_event':
            return bool(candidate.payload_fields.get('result_summary') or candidate.summary)
        if candidate.item_type == 'history_event':
            return bool(candidate.payload_fields.get('reason') or candidate.summary)
        if candidate.item_type == 'todo':
            return bool(candidate.payload_fields.get('priority') and candidate.payload_fields.get('priority_reason'))
        return False


def _response(
    *,
    packet: EvidencePacket,
    item_type: str,
    title: str,
    summary: str,
    payload_fields: dict[str, str],
    confidence_score: float,
) -> MemoryExtractionModelResponse:
    combined_text = _combined_text(packet)
    return MemoryExtractionModelResponse(
        title=title,
        summary=summary,
        item_type=item_type,
        confidence_score=confidence_score,
        input_tokens=max(1, len(combined_text) // 4),
        output_tokens=max(32, len(summary) // 4),
        payload_fields=payload_fields,
    )


def _combined_text(packet: EvidencePacket) -> str:
    return '\n'.join(message.text for message in packet.messages)


def _first_sentence(text: str) -> str:
    return text.strip().split('\n', maxsplit=1)[0][:240]
