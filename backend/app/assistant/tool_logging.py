import logging

logger = logging.getLogger('AssistantTool')


class AssistantToolLogger:
    """AI 비서의 tool/RAG 호출 흐름을 영어 로그로 남깁니다."""

    def log(self, tool_name: str, description: str) -> None:
        safe_tool_name = _ascii(tool_name)
        safe_description = _ascii(description)
        logger.info('[Tool: %s] %s', safe_tool_name, safe_description)


def _ascii(value: object) -> str:
    return str(value).encode('ascii', errors='replace').decode('ascii')
