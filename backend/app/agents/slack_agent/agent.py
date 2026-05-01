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

SLACK_AGENT_NAME = 'slack_agent'
SLACK_AGENT_PROMPT_VERSION = 'slack-timeline:v1'
SLACK_AGENT_MODEL_NAME = 'fake-slack-agent-model'

SLACK_AGENT_MANIFEST = AgentManifest(
    name=SLACK_AGENT_NAME,
    owner='Developer A',
    input_contract='EvidencePacket',
    output_contract='AgentRunResult',
    prompt_versions=(SLACK_AGENT_PROMPT_VERSION,),
    supported_permissions=('internal', 'restricted'),
    capabilities=('timeline_extraction', 'history_generation'),
)


@dataclass(frozen=True)
class SlackAgentModelResponse:
    title: str
    summary: str
    item_type: str
    confidence_score: float
    input_tokens: int
    output_tokens: int
    uncertainty_reason: str | None = None


class SlackAgentModel(Protocol):
    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        raise NotImplementedError


@dataclass(frozen=True)
class SlackAgent:
    model: SlackAgentModel
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
            model_name=SLACK_AGENT_MODEL_NAME,
            token_usage=token_usage,
            input_cost_per_1m=self.input_cost_per_1m,
            output_cost_per_1m=self.output_cost_per_1m,
            cache_hit=False,
        )
        cache_key = build_evidence_cache_key(packet, SLACK_AGENT_PROMPT_VERSION)

        return AgentRunResult(
            agent_name=SLACK_AGENT_NAME,
            prompt_version=SLACK_AGENT_PROMPT_VERSION,
            candidates=[candidate],
            cost=cost,
            cache_key=cache_key,
        )
