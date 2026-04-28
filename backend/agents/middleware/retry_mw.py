from __future__ import annotations

from typing import Any, Callable

import structlog
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging

log = structlog.get_logger(__name__)

# 재시도 가능한 예외 목록
_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
)

try:
    from openai import RateLimitError, APITimeoutError, InternalServerError
    _RETRYABLE_EXCEPTIONS = (*_RETRYABLE_EXCEPTIONS, RateLimitError, APITimeoutError, InternalServerError)
except ImportError:
    pass


@wrap_model_call
def model_retry_middleware(request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
    """지수 백오프 기반 모델 호출 재시도 미들웨어."""

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    def _call() -> ModelResponse:
        return handler(request)

    return _call()
