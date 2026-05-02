import json

from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.slack_agent import (
    SLACK_AGENT_MANIFEST,
    SlackAgent,
    SlackAgentModelResponse,
)
from backend.app.agents.slack_agent.llm import (
    FallbackSlackAgentModel,
    LangChainSlackAgentModel,
    SlackLlmProviderError,
    SlackLlmSettings,
    build_slack_llm_preflight,
    render_slack_llm_prompt,
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


class FakeLangChainResponse:
    content = '{"title":"LLM captured Redis decision","summary":"Redis was selected for queue progress.","item_type":"history_event","confidence_score":0.91}'
    usage_metadata = {'input_tokens': 1200, 'output_tokens': 90}


class FakeLangChainChatModel:
    def __init__(self) -> None:
        self.messages: list = []

    def invoke(self, messages: list) -> FakeLangChainResponse:
        self.messages = messages
        return FakeLangChainResponse()


def test_langchain_slack_agent_model_parses_json_response_and_usage() -> None:
    chat_model = FakeLangChainChatModel()
    model = LangChainSlackAgentModel(
        provider='openai',
        model_name='gpt-test',
        chat_model=chat_model,
    )

    response = model.extract(build_packet())

    assert response.title == 'LLM captured Redis decision'
    assert response.summary == 'Redis was selected for queue progress.'
    assert response.item_type == 'history_event'
    assert response.confidence_score == 0.91
    assert response.input_tokens == 1200
    assert response.output_tokens == 90
    assert response.model_name == 'gpt-test'
    assert chat_model.messages[0][0] == 'system'
    assert 'JSON' in chat_model.messages[0][1]


def test_fallback_slack_agent_model_uses_gemini_when_openai_fails() -> None:
    class FailingModel:
        provider = 'openai'

        def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
            raise SlackLlmProviderError('openai unavailable')

    class GeminiModel:
        provider = 'gemini'

        def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
            return SlackAgentModelResponse(
                title='Gemini fallback candidate',
                summary='Gemini recovered the timeline candidate.',
                item_type='history_event',
                confidence_score=0.82,
                input_tokens=100,
                output_tokens=50,
                model_name='gemini-test',
            )

    model = FallbackSlackAgentModel([FailingModel(), GeminiModel()])

    response = model.extract(build_packet())

    assert response.title == 'Gemini fallback candidate'
    assert response.model_name == 'gemini-test'


def test_slack_llm_preflight_blocks_when_budget_exceeded() -> None:
    packet = build_packet()
    settings = SlackLlmSettings(
        enabled=True,
        provider_order=('openai', 'gemini'),
        openai_api_key='openai-key',
        gemini_api_key='gemini-key',
        max_estimated_cost_usd=0.000001,
    )

    preflight = build_slack_llm_preflight(packet=packet, settings=settings)

    assert preflight['action'] == 'skip'
    assert preflight['budget_status'] == 'over_budget'
    assert preflight['provider_order'] == ['openai', 'gemini']
    assert preflight['estimated_cost_usd'] > preflight['budget_limit_usd']


def test_slack_llm_preflight_reports_missing_credentials_for_all_providers() -> None:
    packet = build_packet()
    settings = SlackLlmSettings(
        enabled=True,
        provider_order=('openai', 'gemini'),
        openai_api_key=None,
        gemini_api_key=None,
    )

    preflight = build_slack_llm_preflight(packet=packet, settings=settings)

    assert preflight['action'] == 'blocked'
    assert preflight['reason'] == 'missing_credentials'
    assert preflight['available_providers'] == []


def test_slack_llm_preflight_estimates_tokens_conservatively_for_capped_prompt() -> None:
    packet = build_packet()
    settings = SlackLlmSettings(
        enabled=True,
        provider_order=('openai', 'gemini'),
        openai_api_key='openai-key',
        gemini_api_key='gemini-key',
        max_estimated_cost_usd=1.0,
        max_input_chars=120,
    )

    preflight = build_slack_llm_preflight(packet=packet, settings=settings)
    prompt = render_slack_llm_prompt(packet, max_input_chars=settings.max_input_chars)

    assert preflight['estimated_input_tokens'] >= len(prompt)


def test_slack_llm_preflight_caps_input_to_budget_affordable_window() -> None:
    packet = build_packet()
    settings = SlackLlmSettings(
        enabled=True,
        provider_order=('openai', 'gemini'),
        openai_api_key='openai-key',
        gemini_api_key='gemini-key',
        max_estimated_cost_usd=0.001,
        max_input_chars=12000,
        max_output_tokens=512,
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
    )

    preflight = build_slack_llm_preflight(packet=packet, settings=settings)

    assert preflight['estimated_input_tokens'] <= 4618
    assert preflight['estimated_cost_usd'] <= preflight['budget_limit_usd']


def test_slack_llm_preflight_reserves_prompt_overhead_for_long_ranked_evidence() -> None:
    packet = EvidencePacket(
        source_type='slack',
        source_window='slack:live:ranked:12',
        messages=[
            EvidenceMessage(
                source_id=f'C123:{index}.000100',
                source_url=f'https://example.slack.com/archives/C123/p{index}000100',
                text=f'결정: 중요한 제품 의사결정 {index}. ' + ('비용 최적화와 배포 검증이 필요합니다. ' * 45),
                author='U123',
                timestamp=f'2026-05-01T09:{index:02d}:00+09:00',
                permission_level='internal',
            )
            for index in range(12)
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )
    settings = SlackLlmSettings(
        enabled=True,
        provider_order=('openai', 'gemini'),
        openai_api_key='openai-key',
        gemini_api_key='gemini-key',
        max_estimated_cost_usd=0.001,
        max_input_chars=12000,
        max_output_tokens=512,
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
    )

    preflight = build_slack_llm_preflight(packet=packet, settings=settings)

    assert preflight['action'] == 'run'
    assert preflight['estimated_cost_usd'] <= preflight['budget_limit_usd']


def test_langchain_slack_agent_model_uses_configured_prompt_cap() -> None:
    chat_model = FakeLangChainChatModel()
    model = LangChainSlackAgentModel(
        provider='openai',
        model_name='gpt-test',
        chat_model=chat_model,
        max_input_chars=24,
    )

    model.extract(build_packet())

    user_payload = chat_model.messages[1][1]
    payload = json.loads(user_payload)
    assert len(payload['evidence'][0]['text']) <= 24
    assert payload['evidence'][0]['text'] != build_packet().messages[0].text
