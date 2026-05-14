from datetime import UTC, datetime
from pathlib import Path


class AssistantToolLogger:
    """AI 비서의 tool/RAG 호출 흐름을 영어 로그로 남깁니다."""

    def __init__(self, log_path: str) -> None:
        self.log_path = Path(log_path)

    def log(self, tool_name: str, description: str) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat()
        safe_tool_name = _ascii(tool_name)
        safe_description = _ascii(description)
        with self.log_path.open('a', encoding='utf-8') as handle:
            handle.write(f'{timestamp} [Tool: {safe_tool_name}] {safe_description}\n')


def _ascii(value: object) -> str:
    return str(value).encode('ascii', errors='replace').decode('ascii')
