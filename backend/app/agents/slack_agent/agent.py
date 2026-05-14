from dataclasses import dataclass, field
from typing import Protocol, Any

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
    capabilities=(
        'timeline_extraction',
        'history_generation',
        'multi_channel_auto_discovery',
        'dm_mpim_extraction',
    ),
)


@dataclass(frozen=True)
class SlackAgentModelResponse:
    title: str
    summary: str
    item_type: str
    confidence_score: float
    input_tokens: int
    output_tokens: int
    model_name: str = SLACK_AGENT_MODEL_NAME
    uncertainty_reason: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)


class SlackAgentModel(Protocol):
    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        raise NotImplementedError


class DeterministicSlackAgentModel:
    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        combined_text = '\n'.join(message.text for message in packet.messages)
        title = '슬랙 타임라인 후보'
        summary = '슬랙 증거 데이터가 검토 가능한 회사 히스토리 후보로 요약되었습니다.'

        if 'Redis' in combined_text or 'redis' in combined_text:
            title = 'Redis 큐 관련 결정사항 추출됨'
            summary = '슬랙 논의 결과, Redis가 큐 및 작업 진행 워크플로우를 지원해야 함을 확인했습니다.'
        elif 'scope' in combined_text.lower():
            title = 'MVP 스코프 팔로업 추출됨'
            summary = '검토가 필요한 MVP 스코프 관련 팔로업 내용이 슬랙 논의에서 확인되었습니다.'
        elif packet.messages:
            first_message = packet.messages[0].source_snippet
            title = '슬랙 히스토리 후보'
            summary = first_message

        input_tokens = max(1, len(combined_text) // 4)
        output_tokens = max(32, len(summary) // 4)

        return SlackAgentModelResponse(
            title=title,
            summary=summary,
            item_type='history_event',
            confidence_score=0.78,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            extra_fields={
                'category': 'Ad-hoc',
                'topic_tag': 'N/A',
                'importance': 'Medium'
            }
        )


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
            payload_fields=model_response.extra_fields,
        )
        candidate.validate_evidence()

        token_usage = TokenUsage(
            input_tokens=model_response.input_tokens,
            output_tokens=model_response.output_tokens,
        )
        cost = estimate_agent_run_cost(
            model_name=model_response.model_name,
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
