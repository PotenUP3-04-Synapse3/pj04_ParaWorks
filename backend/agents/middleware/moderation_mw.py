from __future__ import annotations

import re
from typing import Any, Callable

import structlog
from langchain.agents.middleware import AgentMiddleware, wrap_model_call, ModelRequest, ModelResponse
from langchain.messages import AIMessage

log = structlog.get_logger(__name__)

# 기본 민감 패턴 — 응답 텍스트 검사용
_SENSITIVE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b\d{3}-\d{4}-\d{4}\b'), '[PHONE]'),
    (re.compile(r'\b\d{6}-[1-4]\d{6}\b'), '[RESIDENT_NO]'),
    (re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b'), '[CARD_NO]'),
]


def _scrub_text(text: str) -> str:
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class ContentModerationMiddleware(AgentMiddleware):
    """모델 응답에서 PII 및 민감정보 스크러빙.
    Azure Content Safety가 설정된 경우 추가 검사 수행.
    """

    def after_model(self, state: dict, runtime: Any) -> dict | None:
        messages = state.get('messages', [])
        if not messages:
            return None

        last = messages[-1]
        if not isinstance(last, AIMessage):
            return None

        # 텍스트 콘텐츠 스크러빙
        if isinstance(last.content, str) and last.content:
            scrubbed = _scrub_text(last.content)
            if scrubbed != last.content:
                log.warning('moderation.pii_scrubbed')
                messages[-1] = AIMessage(content=scrubbed, tool_calls=last.tool_calls)
                return {'messages': messages}

        # Azure Content Safety 검사 (선택적)
        self._azure_check(last.content if isinstance(last.content, str) else '')
        return None

    def _azure_check(self, text: str) -> None:
        from backend.core.config import settings
        if not settings.azure_content_safety_endpoint or not text:
            return
        try:
            from azure.ai.contentsafety import ContentSafetyClient  # type: ignore
            from azure.ai.contentsafety.models import AnalyzeTextOptions  # type: ignore
            from azure.core.credentials import AzureKeyCredential  # type: ignore

            client = ContentSafetyClient(
                settings.azure_content_safety_endpoint,
                AzureKeyCredential(settings.azure_content_safety_key),
            )
            response = client.analyze_text(AnalyzeTextOptions(text=text[:5000]))
            for cat in response.categories_analysis:
                if cat.severity and cat.severity >= 4:
                    log.warning('moderation.content_safety_flag', category=cat.category, severity=cat.severity)
        except Exception as exc:
            log.warning('moderation.azure_check_failed', error=str(exc))
