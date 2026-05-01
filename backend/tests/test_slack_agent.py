from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.slack_agent import (
    SLACK_AGENT_MANIFEST,
    SlackAgent,
    SlackAgentModelResponse,
)


class FakeSlackModel:
    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        return SlackAgentModelResponse(
            title='Redis queue decision captured',
            summary='The team agreed to use Redis-backed queues for MVP job progress.',
            item_type='history_event',
            confidence_score=0.84,
            input_tokens=900,
            output_tokens=180,
        )


def build_packet(permission_level: str = 'internal') -> EvidencePacket:
    return EvidencePacket(
        source_type='slack',
        source_window='C123:2026-05-01',
        messages=[
            EvidenceMessage(
                source_id='C123:1777600800.000100',
                source_url='https://example.slack.com/archives/C123/p1777600800000100',
                text='Redis 기반 큐로 MVP 작업 진행 상태를 관리하기로 했습니다.',
                author='U123',
                timestamp='2026-05-01T09:00:00+09:00',
                permission_level=permission_level,
            )
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )


def test_slack_agent_manifest_declares_shared_contracts() -> None:
    assert SLACK_AGENT_MANIFEST.name == 'slack_agent'
    assert SLACK_AGENT_MANIFEST.input_contract == 'EvidencePacket'
    assert SLACK_AGENT_MANIFEST.output_contract == 'AgentRunResult'
    assert 'timeline_extraction' in SLACK_AGENT_MANIFEST.capabilities


def test_slack_agent_creates_evidence_backed_review_candidate() -> None:
    agent = SlackAgent(model=FakeSlackModel())

    result = agent.run(build_packet())

    assert result.agent_name == 'slack_agent'
    assert result.prompt_version == 'slack-timeline:v1'
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.item_type == 'history_event'
    assert candidate.title == 'Redis queue decision captured'
    assert candidate.source_links == ['https://example.slack.com/archives/C123/p1777600800000100']
    assert candidate.source_snippets == ['Redis 기반 큐로 MVP 작업 진행 상태를 관리하기로 했습니다.']
    assert candidate.permission_level == 'internal'
    assert result.cost.model_name == 'fake-slack-agent-model'
    assert result.cost.token_usage.total_tokens == 1080
    assert result.cache_key


def test_slack_agent_preserves_restricted_permission() -> None:
    agent = SlackAgent(model=FakeSlackModel())

    result = agent.run(build_packet(permission_level='restricted'))

    assert result.candidates[0].permission_level == 'restricted'
