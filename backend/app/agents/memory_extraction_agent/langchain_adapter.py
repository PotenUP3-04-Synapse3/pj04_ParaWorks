import json
from typing import Any

from pydantic import BaseModel, Field

from backend.app.agent_runtime import EvidencePacket
from backend.app.agents.memory_extraction_agent.agent import (
    MemoryExtractionModelResponse,
)

DEFAULT_MAX_INPUT_CHARS = 12_000


class StructuredMemoryExtractionOutput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1200)
    item_type: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    payload_fields: dict[str, str] = Field(default_factory=dict)
    uncertainty_reason: str | None = None


class LangChainMemoryExtractionModel:
    def __init__(
        self,
        *,
        chat_model: Any,
        expected_item_type: str,
        task_name: str,
        model_name: str,
        max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    ) -> None:
        self.chat_model = chat_model
        self.expected_item_type = expected_item_type
        self.task_name = task_name
        self.model_name = model_name
        self.max_input_chars = max_input_chars

    def extract(self, packet: EvidencePacket) -> MemoryExtractionModelResponse:
        system_prompt = (
            f'You are performing {self.task_name} for ParaWorks. '
            'Use only the provided evidence. '
            'Return one reviewable candidate through the structured schema. '
            f'The item_type must be {self.expected_item_type}.'
        )
        user_prompt = render_memory_extraction_prompt(
            packet,
            expected_item_type=self.expected_item_type,
            task_name=self.task_name,
            max_input_chars=self.max_input_chars,
        )
        messages = [('system', system_prompt), ('user', user_prompt)]
        structured_model = self.chat_model.with_structured_output(StructuredMemoryExtractionOutput)
        output = _coerce_structured_output(structured_model.invoke(messages))
        summary = output.summary
        return MemoryExtractionModelResponse(
            title=output.title,
            summary=summary,
            item_type=output.item_type or self.expected_item_type,
            confidence_score=output.confidence_score,
            input_tokens=max(1, (len(system_prompt) + len(user_prompt)) // 4),
            output_tokens=max(1, (len(output.title) + len(summary)) // 4),
            payload_fields=output.payload_fields,
            uncertainty_reason=output.uncertainty_reason,
        )


def render_memory_extraction_prompt(
    packet: EvidencePacket,
    *,
    expected_item_type: str,
    task_name: str,
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

    return json.dumps(
        {
            'task': task_name,
            'expected_item_type': expected_item_type,
            'source_window': packet.source_window,
            'requirements': [
                'Use only the provided evidence.',
                'Preserve uncertainty when evidence is weak.',
                'Keep payload_fields aligned with the expected item type.',
            ],
            'evidence': evidence_rows,
        },
        ensure_ascii=False,
    )


def _coerce_structured_output(output: Any) -> StructuredMemoryExtractionOutput:
    if isinstance(output, StructuredMemoryExtractionOutput):
        return output
    if isinstance(output, dict):
        return StructuredMemoryExtractionOutput.model_validate(output)
    if hasattr(output, 'model_dump'):
        return StructuredMemoryExtractionOutput.model_validate(output.model_dump())
    return StructuredMemoryExtractionOutput.model_validate(output)
