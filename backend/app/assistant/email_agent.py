import json
from dataclasses import dataclass, field
from typing import Any

from backend.app.assistant.email_actions import EmailDraft
from backend.app.core.config import Settings

EMAIL_AGENT_PROMPT_VERSION = 'assistant-email-agent:v2'
EMAIL_ACTION_TYPES = {'not_email', 'email_draft', 'needs_clarification', 'general_reply'}


class EmailActionAgentError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailActionDecision:
    action_type: str
    to: list[str] = field(default_factory=list)
    subject: str = ''
    body: str = ''
    clarification_question: str = ''
    reply: str = ''
    confidence_score: float = 1.0
    model_name: str | None = None

    def to_draft(self) -> EmailDraft | None:
        if self.action_type != 'email_draft':
            return None
        if not self.to or not self.subject.strip() or not self.body.strip():
            return None
        return EmailDraft(
            to=[item.strip() for item in self.to if item.strip()],
            subject=self.subject.strip(),
            body=self.body.strip(),
        )


class NoopEmailActionAgent:
    def decide(self, **kwargs) -> EmailActionDecision:
        return EmailActionDecision(action_type='not_email')


class EmailActionAgent:
    def __init__(self, *, model) -> None:
        self.model = model

    def decide(self, *, conversation_context: str, latest_message: str) -> EmailActionDecision:
        try:
            return self.model.decide(
                conversation_context=conversation_context,
                latest_message=latest_message,
            )
        except EmailActionAgentError:
            return EmailActionDecision(action_type='not_email')


class LangChainEmailActionModel:
    def __init__(
        self,
        *,
        chat_model: Any,
        model_name: str,
        max_input_chars: int,
    ) -> None:
        self.chat_model = chat_model
        self.model_name = model_name
        self.max_input_chars = max_input_chars

    def decide(self, *, conversation_context: str, latest_message: str) -> EmailActionDecision:
        messages = [
            (
                'system',
                (
                    'You are a low-cost ParaWorks Email Action sub-agent. '
                    'Classify whether the user wants email action, a brief general reply, or company-memory RAG. '
                    'Use the recent conversation only to resolve recipients, groups, and omitted context. '
                    'Never send email directly. Return strict JSON only.'
                ),
            ),
            (
                'user',
                render_email_action_prompt(
                    conversation_context=conversation_context,
                    latest_message=latest_message,
                    max_input_chars=self.max_input_chars,
                ),
            ),
        ]
        try:
            response = self.chat_model.invoke(messages)
        except Exception as exc:  # pragma: no cover - 외부 LLM provider 장애 경로
            raise EmailActionAgentError(f'{self.model_name} email action model failed: {exc}') from exc

        payload = _parse_json_object(_response_content(response))
        decision = _decision_from_payload(payload)
        return EmailActionDecision(
            action_type=decision.action_type,
            to=decision.to,
            subject=decision.subject,
            body=decision.body,
            clarification_question=decision.clarification_question,
            reply=decision.reply,
            confidence_score=decision.confidence_score,
            model_name=self.model_name,
        )


def build_email_action_agent(settings: Settings) -> EmailActionAgent | NoopEmailActionAgent:
    if settings.paraworks_demo_mode or not settings.assistant_email_agent_enabled or not settings.openai_api_key:
        return NoopEmailActionAgent()

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:  # pragma: no cover - 선택 의존성 누락 경로
        return NoopEmailActionAgent()

    return EmailActionAgent(
        model=LangChainEmailActionModel(
            model_name=settings.assistant_email_agent_model,
            max_input_chars=settings.assistant_email_agent_max_input_chars,
            chat_model=ChatOpenAI(
                model=settings.assistant_email_agent_model,
                api_key=settings.openai_api_key,
                temperature=settings.assistant_email_agent_temperature,
                timeout=settings.assistant_email_agent_timeout_seconds,
                max_tokens=settings.assistant_email_agent_max_output_tokens,
                max_retries=1,
            ),
        )
    )


def render_email_action_context(*, messages: list[Any], max_chars: int) -> str:
    # 최근 대화만 짧게 잘라 저가 모델 호출 비용을 일정하게 제한한다.
    rows = [
        {
            'role': getattr(message, 'role', ''),
            'content': getattr(message, 'content', ''),
        }
        for message in messages[-8:]
    ]
    rendered = json.dumps(rows, ensure_ascii=False)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[-max_chars:]


def render_email_action_prompt(
    *,
    conversation_context: str,
    latest_message: str,
    max_input_chars: int,
) -> str:
    payload = {
        'prompt_version': EMAIL_AGENT_PROMPT_VERSION,
        'task': 'Route the latest user message before the expensive RAG answer agent runs.',
        'conversation_context': conversation_context[-max_input_chars:],
        'latest_message': latest_message,
        'rules': [
            'If the latest message asks to write, draft, send, forward, or email someone, return action_type=email_draft.',
            'Use previous conversation context to resolve omitted recipients or referenced people.',
            'If an email action is requested but the recipient or content is missing, return action_type=needs_clarification.',
            'If the latest message only asks for a greeting, wording help, or a short non-company-memory response, return action_type=general_reply.',
            'If the user is asking a knowledge question or does not want email, return action_type=not_email.',
            'For email_draft, write a concise Korean business subject and body.',
            'For general_reply, write a concise Korean reply and leave email fields empty.',
            'Return confidence_score between 0 and 1. Use low confidence when the intent is ambiguous.',
            'Do not require RAG evidence for ordinary email composition requests.',
            'Never invent a recipient that is not in the latest message or conversation context.',
        ],
        'json_schema': {
            'action_type': 'not_email | email_draft | needs_clarification | general_reply',
            'to': ['recipient@example.com'],
            'subject': 'Korean business email subject',
            'body': 'Korean business email body',
            'clarification_question': 'Korean question when required information is missing',
            'reply': 'Korean reply for general_reply',
            'confidence_score': 0.0,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _decision_from_payload(payload: dict[str, Any]) -> EmailActionDecision:
    action_type = str(payload.get('action_type') or 'not_email').strip()
    if action_type not in EMAIL_ACTION_TYPES:
        action_type = 'not_email'

    to = payload.get('to') or []
    if not isinstance(to, list):
        to = []
    recipients = [str(item).strip() for item in to if str(item).strip()]

    return EmailActionDecision(
        action_type=action_type,
        to=recipients,
        subject=str(payload.get('subject') or '').strip(),
        body=str(payload.get('body') or '').strip(),
        clarification_question=str(payload.get('clarification_question') or '').strip(),
        reply=str(payload.get('reply') or '').strip(),
        confidence_score=_confidence_score(payload.get('confidence_score')),
    )


def _confidence_score(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(parsed, 1.0))


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`').strip()
        if cleaned.lower().startswith('json'):
            cleaned = cleaned[4:].strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise EmailActionAgentError('email action model returned invalid JSON') from exc
    if not isinstance(payload, dict):
        raise EmailActionAgentError('email action model returned non-object JSON')
    return payload


def _response_content(response: Any) -> str:
    content = getattr(response, 'content', response)
    if isinstance(content, list):
        return ''.join(str(part.get('text', part)) if isinstance(part, dict) else str(part) for part in content)
    return str(content)
