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

MAIL_DOCUMENT_AGENT_NAME = 'mail_document_agent'
MAIL_DOCUMENT_AGENT_PROMPT_VERSION = 'mail-document-history:v1'
MAIL_DOCUMENT_AGENT_MODEL_NAME = 'fake-mail-document-agent-model'

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
    title: str
    summary: str
    item_type: str
    confidence_score: float
    input_tokens: int
    output_tokens: int
    uncertainty_reason: str | None = None


class MailDocumentAgentModel(Protocol):
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        raise NotImplementedError


class DeterministicMailDocumentAgentModel:
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        combined_text = '\n'.join(message.text for message in packet.messages)
        title = 'Mail and document history candidate'
        summary = 'Gmail and Drive evidence was summarized into a reviewable company memory candidate.'
        item_type = 'history_event'

        if 'PostgreSQL' in combined_text and 'Redis' in combined_text:
            title = 'Redis and PostgreSQL responsibility decision'
            summary = 'Mail and document evidence indicates Redis handles transient job state while PostgreSQL remains the durable source of record.'
            item_type = 'decision'
        elif 'confidential pricing' in combined_text.lower():
            title = 'Restricted document evidence requires review'
            summary = 'Drive evidence contains restricted pricing context that should stay behind permission checks.'
            item_type = 'history_event'
        elif packet.messages:
            summary = packet.messages[0].source_snippet

        input_tokens = max(1, len(combined_text) // 4)
        output_tokens = max(32, len(summary) // 4)

        return MailDocumentAgentModelResponse(
            title=title,
            summary=summary,
            item_type=item_type,
            confidence_score=0.8,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


@dataclass(frozen=True)
class MailDocumentAgent:
    model: MailDocumentAgentModel
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
        )
        candidate.validate_evidence()

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
        cache_key = build_evidence_cache_key(packet, MAIL_DOCUMENT_AGENT_PROMPT_VERSION)

        return AgentRunResult(
            agent_name=MAIL_DOCUMENT_AGENT_NAME,
            prompt_version=MAIL_DOCUMENT_AGENT_PROMPT_VERSION,
            candidates=[candidate],
            cost=cost,
            cache_key=cache_key,
        )
