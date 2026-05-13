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

# 메일 및 문서 에이전트의 상수 정의
MAIL_DOCUMENT_AGENT_NAME = 'mail_document_agent'
MAIL_DOCUMENT_AGENT_PROMPT_VERSION = 'mail-document-history:v1'
MAIL_DOCUMENT_AGENT_MODEL_NAME = 'fake-mail-document-agent-model'

# 에이전트의 명세(Manifest) 정의: 소유자, 권한, 기능 등을 기술
MAIL_DOCUMENT_AGENT_MANIFEST = AgentManifest(
    name=MAIL_DOCUMENT_AGENT_NAME,
    owner='Developer B',
    input_contract='EvidencePacket',
    output_contract='AgentRunResult',
    prompt_versions=(MAIL_DOCUMENT_AGENT_PROMPT_VERSION,),
    supported_permissions=('internal', 'restricted'),
    capabilities=('timeline_extraction', 'history_generation', 'decision_extraction'),
)


@dataclass(frozen=True)
class MailDocumentAgentModelResponse:
    """에이전트 모델의 추출 결과 데이터 구조"""
    title: str
    summary: str
    item_type: str
    confidence_score: float
    input_tokens: int
    output_tokens: int
    model_name: str | None = None
    uncertainty_reason: str | None = None
    is_business_related: bool = True
    project_tag: str | None = None
    structured_data: dict[str, str] | None = None


class MailDocumentAgentModel(Protocol):
    """에이전트 모델이 구현해야 할 인터페이스(프로토콜)"""
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        raise NotImplementedError


class DeterministicMailDocumentAgentModel:
    """LLM 없이 규칙 기반으로 정보를 추출하는 테스트용 결정론적 모델"""
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        combined_text = '\n'.join(message.text for message in packet.messages)
        title = 'Mail and document history candidate'
        summary = 'Gmail and Drive evidence was summarized into a reviewable company memory candidate.'
        item_type = 'history_event'

        # 특정 키워드에 따른 결과 분류 로직
        if 'PostgreSQL' in combined_text and 'Redis' in combined_text:
            title = 'Redis and PostgreSQL responsibility decision'
            summary = 'Mail and document evidence indicates Redis handles transient job state while PostgreSQL remains the durable source of record.'
            item_type = 'decision'
        elif 'confidential pricing' in combined_text.lower():
            title = 'Restricted document evidence requires review'
            summary = 'Drive evidence contains restricted pricing context that should stay behind permission checks.'
            item_type = 'history_event'
        elif 'budget' in combined_text.lower() or 'revenue' in combined_text.lower():
            title = 'Quarterly budget and revenue strategy updated'
            summary = 'Parsed document evidence suggests an update to the quarterly budget and hiring plan.'
            item_type = 'history_event'
        elif 'contract review' in combined_text.lower() or 'due friday' in combined_text.lower():
            title = 'Contract review scheduled'
            summary = 'Extracted todo item from email/document indicating a contract review needs to be completed by Friday.'
            item_type = 'todo'
        elif packet.messages:
            summary = packet.messages[0].source_snippet

        # 토큰 사용량 및 신뢰도 계산 (모의 계산)
        input_tokens = max(1, len(combined_text) // 4)
        output_tokens = max(32, len(summary) // 4)
        confidence_score = 0.8
        uncertainty_reason = _parser_uncertainty_reason(packet)
        if uncertainty_reason:
            confidence_score = _parser_uncertainty_confidence(packet)

        return MailDocumentAgentModelResponse(
            title=title,
            summary=summary,
            item_type=item_type,
            confidence_score=confidence_score,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            uncertainty_reason=uncertainty_reason,
            is_business_related=True,
            project_tag='General',
            structured_data={},
        )


@dataclass(frozen=True)
class MailDocumentAgent:
    """메일 및 문서 데이터를 처리하여 검토 후보를 생성하는 에이전트 클래스"""
    model: MailDocumentAgentModel
    input_cost_per_1m: float = 0.15
    output_cost_per_1m: float = 0.60

    def run(self, packet: EvidencePacket) -> AgentRunResult:
        """증거 패킷을 입력받아 모델을 실행하고 결과를 AgentRunResult로 반환"""
        model_response = self.model.extract(packet)

        candidates = []
        if model_response.is_business_related:
            payload_fields = model_response.structured_data or {}
            if model_response.project_tag:
                payload_fields['project_tag'] = model_response.project_tag

            # 검토 큐(Review Queue)에 들어갈 후보 생성
            candidate = ReviewCandidate(
                item_type=model_response.item_type,
                title=model_response.title,
                summary=model_response.summary,
                source_links=packet.source_links,
                source_snippets=packet.source_snippets,
                confidence_score=model_response.confidence_score,
                permission_level=packet.strictest_permission,
                uncertainty_reason=model_response.uncertainty_reason,
                payload_fields=payload_fields,
            )
            # 증거 데이터 유효성 검증 (증거 없는 후보 생성 방지)
            candidate.validate_evidence()
            candidates.append(candidate)

        # 비용 및 토큰 사용량 기록
        token_usage = TokenUsage(
            input_tokens=model_response.input_tokens,
            output_tokens=model_response.output_tokens,
        )
        cost = estimate_agent_run_cost(
            model_name=MAIL_DOCUMENT_AGENT_MODEL_NAME,
            token_usage=token_usage,
            input_cost_per_1m=self.input_cost_per_1m,
            output_cost_per_1m=self.output_cost_per_1m,
            cache_hit=False,
        )
        # 캐싱을 위한 키 생성
        cache_key = build_evidence_cache_key(packet, MAIL_DOCUMENT_AGENT_PROMPT_VERSION)

        return AgentRunResult(
            agent_name=MAIL_DOCUMENT_AGENT_NAME,
            prompt_version=MAIL_DOCUMENT_AGENT_PROMPT_VERSION,
            candidates=candidates,
            cost=cost,
            cache_key=cache_key,
        )


def _parser_uncertainty_reason(packet: EvidencePacket) -> str | None:
    """문서 파싱 상태가 불완전한 경우 그 이유를 추출하는 헬퍼 함수"""
    uncertain_messages = [
        message
        for message in packet.messages
        if message.metadata.get('source_type') == 'drive'
        and message.metadata.get('parser_status')
        and message.metadata.get('parser_status') != 'parsed'
    ]
    if not uncertain_messages:
        return None
    details = []
    for message in uncertain_messages:
        status = message.metadata.get('parser_status')
        reason = message.metadata.get('parser_status_reason') or 'unknown_reason'
        details.append(f'{message.source_id}={status}({reason})')
    return f"Some document evidence is not body-parsed: {', '.join(details)}"


def _parser_uncertainty_confidence(packet: EvidencePacket) -> float:
    """파싱 상태에 따라 신뢰도 점수를 조정하는 헬퍼 함수"""
    statuses = {
        str(message.metadata.get('parser_status'))
        for message in packet.messages
        if message.metadata.get('source_type') == 'drive'
    }
    if 'unsupported' in statuses:
        return 0.3 # 지원되지 않는 형식인 경우 낮은 신뢰도
    return 0.42 # 일반적인 파싱 오류/제한 사항인 경우 중간 신뢰도
