import json
from dataclasses import dataclass
from typing import Any

from backend.app.agent_runtime import (
    EvidencePacket,
    TokenUsage,
    evaluate_agent_cost_budget,
)
from backend.app.agents.slack_agent.agent import SlackAgentModelResponse

DEFAULT_OPENAI_MODEL = 'gpt-5.4-mini'
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'
DEFAULT_INPUT_COST_PER_1M = 0.15
DEFAULT_OUTPUT_COST_PER_1M = 0.60
DEFAULT_MAX_OUTPUT_TOKENS = 512
DEFAULT_MAX_INPUT_CHARS = 12_000
DEFAULT_PROMPT_OVERHEAD_CHARS = 1_500
OPENAI_COMPATIBLE_PROVIDERS = {'openai', 'azure_openai'}


class SlackLlmProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlackLlmSettings:
    enabled: bool = False
    provider_order: tuple[str, ...] = ('openai', 'gemini')
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_model: str = DEFAULT_OPENAI_MODEL
    gemini_model: str = DEFAULT_GEMINI_MODEL
    input_cost_per_1m: float = DEFAULT_INPUT_COST_PER_1M
    output_cost_per_1m: float = DEFAULT_OUTPUT_COST_PER_1M
    max_estimated_cost_usd: float | None = 0.001
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS
    max_evidence_messages: int = 12
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    temperature: float = 0.2
    timeout_seconds: float = 30.0


class LangChainSlackAgentModel:
    def __init__(
        self,
        *,
        provider: str,
        model_name: str,
        chat_model: Any,
        max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.chat_model = chat_model
        self.max_input_chars = max_input_chars

    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        messages = [
            (
                'system',
                'You extract one reviewable company history candidate from Slack evidence. '
                'The title and summary must be written in Korean. '
                'Return only JSON with title, summary, item_type, confidence_score, and optional uncertainty_reason.',
            ),
            ('user', render_slack_llm_prompt(packet, max_input_chars=self.max_input_chars)),
        ]
        try:
            response = self.chat_model.invoke(messages)
        except Exception as exc:  # pragma: no cover - provider-specific branch
            raise SlackLlmProviderError(f'{self.provider} provider failed: {exc}') from exc

        payload = _parse_json_content(_response_content(response))
        input_tokens, output_tokens = _usage_tokens(response, messages, payload)
        return SlackAgentModelResponse(
            title=str(payload.get('title') or 'Slack LLM history candidate')[:200],
            summary=str(payload.get('summary') or 'Slack evidence was summarized by the LLM.')[:1200],
            item_type=_safe_item_type(payload.get('item_type')),
            confidence_score=_safe_confidence(payload.get('confidence_score')),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=self.model_name,
            uncertainty_reason=payload.get('uncertainty_reason'),
        )


class FallbackSlackAgentModel:
    def __init__(self, providers: list[Any]) -> None:
        self.providers = providers

    def extract(self, packet: EvidencePacket) -> SlackAgentModelResponse:
        errors: list[str] = []
        for provider in self.providers:
            try:
                return provider.extract(packet)
            except SlackLlmProviderError as exc:
                provider_name = getattr(provider, 'provider', 'unknown')
                errors.append(f'{provider_name}: {exc}')
        raise SlackLlmProviderError('; '.join(errors) or 'no LLM providers configured')


def build_slack_llm_preflight(*, packet: EvidencePacket, settings: SlackLlmSettings) -> dict[str, Any]:
    provider_order = _clean_provider_order(settings.provider_order)
    available_providers = _available_providers(provider_order, settings)
    if not settings.enabled:
        return _preflight_response(
            action='blocked',
            reason='llm_disabled',
            budget_status='disabled',
            provider_order=provider_order,
            available_providers=available_providers,
            settings=settings,
            packet=packet,
        )
    if not packet.messages:
        return _preflight_response(
            action='skip',
            reason='no_input',
            budget_status='no_input',
            provider_order=provider_order,
            available_providers=available_providers,
            settings=settings,
            packet=packet,
        )
    if not available_providers:
        return _preflight_response(
            action='blocked',
            reason='missing_credentials',
            budget_status='missing_credentials',
            provider_order=provider_order,
            available_providers=available_providers,
            settings=settings,
            packet=packet,
        )

    model_name = _model_for_provider(available_providers[0], settings)
    token_usage = _estimated_token_usage(packet, settings)
    decision = evaluate_agent_cost_budget(
        model_name=model_name,
        token_usage=token_usage,
        input_cost_per_1m=settings.input_cost_per_1m,
        output_cost_per_1m=settings.output_cost_per_1m,
        max_cost_usd=settings.max_estimated_cost_usd,
        cache_hit=False,
    )
    return {
        'action': decision.action,
        'reason': decision.reason,
        'budget_status': decision.budget_status,
        'model_name': decision.model_name,
        'provider_order': list(provider_order),
        'available_providers': available_providers,
        'estimated_input_tokens': decision.token_usage.input_tokens,
        'estimated_output_tokens': decision.token_usage.output_tokens,
        'estimated_total_tokens': decision.token_usage.total_tokens,
        'estimated_cost_usd': round(decision.estimated_cost_usd, 6),
        'budget_limit_usd': decision.budget_limit_usd,
        'evidence_message_count': len(packet.messages),
        'max_evidence_messages': settings.max_evidence_messages,
        'requires_paid_confirmation': True,
    }


def build_langchain_slack_agent_model(settings: SlackLlmSettings) -> FallbackSlackAgentModel:
    providers = []
    for provider in _available_providers(_clean_provider_order(settings.provider_order), settings):
        if provider in OPENAI_COMPATIBLE_PROVIDERS:
            providers.append(_build_openai_model(settings, provider=provider))
        elif provider == 'gemini':
            providers.append(_build_gemini_model(settings))
    if not providers:
        raise SlackLlmProviderError('No LLM providers have credentials')
    return FallbackSlackAgentModel(providers)


def render_slack_llm_prompt(
    packet: EvidencePacket,
    *,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> str:
    evidence_rows = []
    remaining_chars = max_input_chars
    for message in packet.messages:
        text = message.text[: max(0, min(len(message.text), remaining_chars))]
        remaining_chars -= len(text)
        evidence_rows.append(
            {
                'source_id': message.source_id,
                'source_url': message.source_url,
                'timestamp': message.timestamp,
                'author': message.author,
                'permission_level': message.permission_level,
                'text': text,
            }
        )
        if remaining_chars <= 0:
            break

    # ?숈쟻 ?꾨줈?앺듃 紐⑸줉 二쇱엯
    projects_context = packet.context.get('projects', [])
    project_descriptions = [f"{p['name']} ({p['project_key']}): {p['summary']}" for p in projects_context]
    if not project_descriptions:
        project_descriptions = ["吏꾪뻾 以묒씤 怨듭떇 ?꾨줈?앺듃媛 ?꾩쭅 ?놁뒿?덈떎."]

    return json.dumps(
        {
            'task': 'Extract Slack-based company history candidates for human review.',
            'allowed_item_types': ['history_event', 'decision_record', 'todo'],
            'category_guide': 'Project, Operations, Administration, Ad-hoc',
            'importance_guide': 'Low, Medium, High',
            'current_projects': project_descriptions,
            'requirements': [
                'Use only the provided evidence.',
                'The title and summary must be written in Korean.',
                'Keep the summary concise and business-friendly.',
                'Set confidence_score between 0 and 1.',
                'Assign category, topic_tag, and importance to each candidate.',
                'For topic_tag, CHOOSE EXACTLY ONE from the current_projects list. If none fit, invent a short new topic name, or use "Ad-hoc" if it\'s just general chatter.',
            ],
            'source_window': packet.source_window,
            'evidence': evidence_rows,
        },
        ensure_ascii=False,
    )


def _build_openai_model(settings: SlackLlmSettings, *, provider: str = 'openai') -> LangChainSlackAgentModel:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise SlackLlmProviderError('langchain-openai is not installed') from exc
    return LangChainSlackAgentModel(
        provider=provider,
        model_name=settings.openai_model,
        max_input_chars=_effective_max_input_chars(settings),
        chat_model=ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.temperature,
            timeout=settings.timeout_seconds,
            max_retries=1,
        ),
    )


def _build_gemini_model(settings: SlackLlmSettings) -> LangChainSlackAgentModel:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise SlackLlmProviderError('langchain-google-genai is not installed') from exc
    return LangChainSlackAgentModel(
        provider='gemini',
        model_name=settings.gemini_model,
        max_input_chars=_effective_max_input_chars(settings),
        chat_model=ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=settings.temperature,
            timeout=settings.timeout_seconds,
            max_retries=1,
        ),
    )


def _preflight_response(
    *,
    action: str,
    reason: str,
    budget_status: str,
    provider_order: tuple[str, ...],
    available_providers: list[str],
    settings: SlackLlmSettings,
    packet: EvidencePacket,
) -> dict[str, Any]:
    token_usage = _estimated_token_usage(packet, settings)
    return {
        'action': action,
        'reason': reason,
        'budget_status': budget_status,
        'model_name': _model_for_provider(available_providers[0], settings) if available_providers else None,
        'provider_order': list(provider_order),
        'available_providers': available_providers,
        'estimated_input_tokens': token_usage.input_tokens,
        'estimated_output_tokens': token_usage.output_tokens,
        'estimated_total_tokens': token_usage.total_tokens,
        'estimated_cost_usd': 0.0,
        'budget_limit_usd': settings.max_estimated_cost_usd,
        'evidence_message_count': len(packet.messages),
        'max_evidence_messages': settings.max_evidence_messages,
        'requires_paid_confirmation': True,
    }


def _estimated_token_usage(packet: EvidencePacket, settings: SlackLlmSettings) -> TokenUsage:
    max_input_chars = _effective_max_input_chars(settings)
    prompt = render_slack_llm_prompt(packet, max_input_chars=max_input_chars)
    affordable_prompt_chars = _affordable_prompt_chars(settings)
    for _ in range(4):
        if affordable_prompt_chars is None or len(prompt) <= affordable_prompt_chars or max_input_chars <= 0:
            break
        overage = len(prompt) - affordable_prompt_chars
        max_input_chars = max(0, max_input_chars - overage - 128)
        prompt = render_slack_llm_prompt(packet, max_input_chars=max_input_chars)
    return TokenUsage(
        input_tokens=max(1, len(prompt)),
        output_tokens=settings.max_output_tokens,
    )


def _effective_max_input_chars(settings: SlackLlmSettings) -> int:
    affordable_prompt_chars = _affordable_prompt_chars(settings)
    if affordable_prompt_chars is None:
        return settings.max_input_chars
    affordable_evidence_chars = affordable_prompt_chars - DEFAULT_PROMPT_OVERHEAD_CHARS
    return max(0, min(settings.max_input_chars, affordable_evidence_chars))


def _affordable_prompt_chars(settings: SlackLlmSettings) -> int | None:
    if settings.max_estimated_cost_usd is None:
        return None
    total_budget_units = settings.max_estimated_cost_usd * 1_000_000
    reserved_output_units = settings.max_output_tokens * settings.output_cost_per_1m
    remaining_input_units = total_budget_units - reserved_output_units
    if remaining_input_units <= 0:
        return 0
    return int(remaining_input_units // settings.input_cost_per_1m)


def _available_providers(provider_order: tuple[str, ...], settings: SlackLlmSettings) -> list[str]:
    available = []
    for provider in provider_order:
        if provider in OPENAI_COMPATIBLE_PROVIDERS and settings.openai_api_key:
            available.append(provider)
        if provider == 'gemini' and settings.gemini_api_key:
            available.append(provider)
    return available


def _clean_provider_order(provider_order: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    cleaned = []
    for provider in provider_order:
        normalized = provider.strip().lower()
        if normalized in {*OPENAI_COMPATIBLE_PROVIDERS, 'gemini'} and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    return tuple(cleaned) or ('openai', 'gemini')


def _model_for_provider(provider: str, settings: SlackLlmSettings) -> str:
    return settings.gemini_model if provider == 'gemini' else settings.openai_model


def _response_content(response: Any) -> str:
    content = getattr(response, 'content', response)
    if isinstance(content, list):
        return ''.join(str(part.get('text', part)) if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`')
        cleaned = cleaned.removeprefix('json').strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SlackLlmProviderError('LLM response was not valid JSON') from exc
    if not isinstance(payload, dict):
        raise SlackLlmProviderError('LLM response JSON must be an object')
    return payload


def _usage_tokens(response: Any, messages: list[tuple[str, str]], payload: dict[str, Any]) -> tuple[int, int]:
    usage = getattr(response, 'usage_metadata', None) or getattr(response, 'response_metadata', {}).get('token_usage', {})
    input_tokens = usage.get('input_tokens') or usage.get('prompt_tokens')
    output_tokens = usage.get('output_tokens') or usage.get('completion_tokens')
    if input_tokens is None:
        input_tokens = max(1, sum(len(message[1]) for message in messages) // 4)
    if output_tokens is None:
        output_tokens = max(1, len(json.dumps(payload, ensure_ascii=False)) // 4)
    return int(input_tokens), int(output_tokens)


def _safe_item_type(raw_item_type: Any) -> str:
    item_type = str(raw_item_type or 'history_event')
    return item_type if item_type in {'history_event', 'decision_record', 'todo'} else 'history_event'


def _safe_confidence(raw_confidence: Any) -> float:
    try:
        return min(max(float(raw_confidence), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.7
