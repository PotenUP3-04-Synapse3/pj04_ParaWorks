import json
from typing import Any

from backend.app.agent_runtime import (
    EvidencePacket,
)
from backend.app.agents.mail_document_agent.agent import MailDocumentAgentModelResponse

# 입력 가능한 최대 문자 수 제한
DEFAULT_MAX_INPUT_CHARS = 12_000

class MailDocumentLlmProviderError(RuntimeError):
    """LLM 프로바이더 실행 중 발생하는 예외 클래스"""
    pass

class LangChainMailDocumentAgentModel:
    """LangChain을 사용하여 실제 LLM으로 정보를 추출하는 에이전트 모델"""
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

    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        """LLM을 호출하여 메일/문서 증거로부터 구조화된 정보를 추출"""
        messages = [
            (
                'system',
                'You extract one reviewable company history candidate or decision from Gmail/Drive evidence. '
                'The title and summary must be written in Korean. '
                'Determine if the evidence is business-related. If it is purely personal/private, set is_business_related=false. '
                'Extract project tag if applicable. '
                'Also extract structured info: for Gmail (To, From, Subject, CC, Date, Summary, Link), for Drive (Uploader, Title, Upload Date, Summary, Link). '
                'Return ONLY JSON with fields: title, summary, item_type, confidence_score, is_business_related (bool), project_tag (string), structured_data (dict), and optional uncertainty_reason.',
            ),
            ('user', render_mail_docs_llm_prompt(packet, max_input_chars=self.max_input_chars)),
        ]
        try:
            # LangChain 모델 호출
            response = self.chat_model.invoke(messages)
        except Exception as exc:
            raise MailDocumentLlmProviderError(f'{self.provider} provider failed: {exc}') from exc

        # 응답 파싱 및 결과 구조화
        payload = _parse_json_content(_response_content(response))
        input_tokens, output_tokens = _usage_tokens(response, messages, payload)
        
        return MailDocumentAgentModelResponse(
            title=str(payload.get('title') or 'Mail/Docs LLM candidate')[:200],
            summary=str(payload.get('summary') or 'Evidence was summarized by the LLM.')[:1200],
            item_type=_safe_item_type(payload.get('item_type')),
            confidence_score=_safe_confidence(payload.get('confidence_score')),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=self.model_name,
            uncertainty_reason=payload.get('uncertainty_reason'),
            is_business_related=bool(payload.get('is_business_related', True)),
            project_tag=payload.get('project_tag'),
            structured_data=payload.get('structured_data', {}),
        )

def render_mail_docs_llm_prompt(
    packet: EvidencePacket,
    *,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> str:
    """증거 패킷을 LLM 프롬프트용 JSON 문자열로 변환"""
    evidence_rows = []
    remaining_chars = max_input_chars
    for message in packet.messages:
        text = message.text[: max(0, min(len(message.text), remaining_chars))]
        remaining_chars -= len(text)
        evidence_rows.append(
            {
                'source_type': message.metadata.get('source_type', 'unknown'),
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

    return json.dumps(
        {
            'task': 'Extract structured output and tag projects from mail/document evidence.',
            'allowed_item_types': ['history_event', 'decision_record', 'todo'],
            'requirements': [
                'Use only the provided evidence.',
                'The title and summary must be written in Korean.',
                'Identify if it is business related.',
                'Assign a project_tag if a specific project is mentioned.',
                'Populate structured_data dictionary with specific fields based on source_type (Gmail or Drive).',
            ],
            'source_window': packet.source_window,
            'evidence': evidence_rows,
        },
        ensure_ascii=False,
    )

def _response_content(response: Any) -> str:
    """LLM 응답 객체에서 텍스트 본문을 추출"""
    content = getattr(response, 'content', response)
    if isinstance(content, list):
        return ''.join(str(part.get('text', part)) if isinstance(part, dict) else str(part) for part in content)
    return str(content)

def _parse_json_content(content: str) -> dict[str, Any]:
    """LLM이 반환한 문자열에서 JSON 마크다운 등을 제거하고 딕셔너리로 파싱"""
    cleaned = content.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`')
        cleaned = cleaned.removeprefix('json').strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise MailDocumentLlmProviderError('LLM response was not valid JSON') from exc
    if not isinstance(payload, dict):
        raise MailDocumentLlmProviderError('LLM response JSON must be an object')
    return payload

def _usage_tokens(response: Any, messages: list[tuple[str, str]], payload: dict[str, Any]) -> tuple[int, int]:
    """LLM 응답에서 사용된 토큰 수를 추출하거나, 없는 경우 어림치 계산"""
    usage = getattr(response, 'usage_metadata', None) or getattr(response, 'response_metadata', {}).get('token_usage', {})
    input_tokens = usage.get('input_tokens') or usage.get('prompt_tokens')
    output_tokens = usage.get('output_tokens') or usage.get('completion_tokens')
    if input_tokens is None:
        input_tokens = max(1, sum(len(message[1]) for message in messages) // 4)
    if output_tokens is None:
        output_tokens = max(1, len(json.dumps(payload, ensure_ascii=False)) // 4)
    return int(input_tokens), int(output_tokens)

def _safe_item_type(raw_item_type: Any) -> str:
    """추출된 아이템 타입이 허용된 범위 내에 있는지 확인"""
    item_type = str(raw_item_type or 'history_event')
    return item_type if item_type in {'history_event', 'decision_record', 'todo'} else 'history_event'

def _safe_confidence(raw_confidence: Any) -> float:
    """신뢰도 점수를 0.0 ~ 1.0 사이로 조정"""
    try:
        return min(max(float(raw_confidence), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.7
