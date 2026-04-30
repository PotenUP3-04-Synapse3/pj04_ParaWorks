from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import decode_token

logger = structlog.get_logger()

# ── Paths that skip authentication ──────────────────────────────────────────
_PUBLIC_PATHS = {
    '/',
    '/health',
    '/api/v1/auth/login',
    '/api/v1/auth/google/callback',
    '/api/v1/auth/refresh',
    '/api/v1/webhooks/slack',
    '/api/v1/webhooks/google-drive',
    '/api/v1/webhooks/github',
    # Swagger / ReDoc (개발 환경)
    '/api/docs',
    '/api/redoc',
    '/api/openapi.json',
    # 하위 호환 (기본 경로)
    '/docs',
    '/redoc',
    '/openapi.json',
}


_PUBLIC_PATH_PREFIXES = (
    '/api/docs',
    '/api/redoc',
    '/api/openapi.json',
    '/docs',
    '/redoc',
)

class AuthMiddleware(BaseHTTPMiddleware):
    """Validate JWT on every non-public request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith(_PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return JSONResponse(status_code=401, content={'detail': 'Missing token'})

        token = auth.removeprefix('Bearer ').strip()
        try:
            payload = decode_token(token)
            if payload.get('type') != 'access':
                raise JWTError('Not an access token')
            request.state.user_id = payload.get('sub')
            request.state.org_id = payload.get('org_id')
            request.state.role = payload.get('role', 'member')
        except JWTError:
            return JSONResponse(status_code=401, content={'detail': 'Invalid or expired token'})

        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Record every mutating request to the audit log queue."""

    _AUDIT_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if (
            request.method in self._AUDIT_METHODS
            and request.url.path not in _PUBLIC_PATHS
            and hasattr(request.state, 'user_id')
        ):
            # Fire-and-forget: don't block the response
            try:
                from app.tasks.audit_tasks import record_audit_log

                record_audit_log.delay(
                    user_id=request.state.user_id,
                    action=request.method,
                    resource_path=request.url.path,
                    ip_addr=_get_client_ip(request),
                    user_agent=request.headers.get('user-agent', ''),
                    status_code=response.status_code,
                )
            except Exception:
                pass  # Never block on audit logging

        return response


class LatencyLoggingMiddleware(BaseHTTPMiddleware):
    """Log request latency for every API call."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            'http_request',
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(elapsed_ms, 2),
        )
        response.headers['X-Response-Time'] = f'{elapsed_ms:.2f}ms'
        return response


class LLMTokenLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request-scoped LLM token counter; log totals after response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.llm_tokens = {'prompt': 0, 'completion': 0}
        response = await call_next(request)

        tokens = request.state.llm_tokens
        if tokens['prompt'] or tokens['completion']:
            logger.info(
                'llm_tokens',
                path=request.url.path,
                prompt_tokens=tokens['prompt'],
                completion_tokens=tokens['completion'],
                total=tokens['prompt'] + tokens['completion'],
            )
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID to every request/response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers['X-Request-ID'] = req_id
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return a structured JSON error."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception('unhandled_error', path=request.url.path, error=str(exc))
            return JSONResponse(
                status_code=500,
                content={
                    'detail': 'Internal server error',
                    'request_id': getattr(request.state, 'request_id', None),
                },
            )


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'
