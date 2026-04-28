from __future__ import annotations

import time
from typing import Any

import structlog
from langchain.agents.middleware import AgentMiddleware, wrap_model_call, wrap_tool_call
from langchain.agents.middleware import ModelRequest, ModelResponse

log = structlog.get_logger(__name__)


class ToolCallLoggingMiddleware(AgentMiddleware):
    """모든 tool call 및 model 요청/응답을 structlog로 기록."""

    def before_model(self, state: dict, runtime: Any) -> dict | None:
        log.info(
            'agent.before_model',
            message_count=len(state.get('messages', [])),
        )
        return {'_model_start_time': time.perf_counter()}

    def after_model(self, state: dict, runtime: Any) -> dict | None:
        start = state.pop('_model_start_time', None)
        elapsed = round(time.perf_counter() - start, 3) if start else None
        messages = state.get('messages', [])
        last_msg = messages[-1] if messages else None
        tool_calls = getattr(last_msg, 'tool_calls', []) if last_msg else []

        log.info(
            'agent.after_model',
            elapsed_sec=elapsed,
            tool_calls=[tc['name'] for tc in tool_calls],
        )
        return None


@wrap_tool_call
def tool_call_logger(request: Any, handler: Any) -> Any:
    """개별 tool call 실행 로깅."""
    name = request.tool_call.get('name', 'unknown')
    args = request.tool_call.get('args', {})
    log.info('tool.call', tool=name, args=args)
    start = time.perf_counter()
    try:
        result = handler(request)
        log.info('tool.success', tool=name, elapsed=round(time.perf_counter() - start, 3))
        return result
    except Exception as exc:
        log.error('tool.error', tool=name, error=str(exc))
        raise
