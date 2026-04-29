"""FastAPI application entry point."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.middleware import (
    AuthMiddleware,
    AuditLogMiddleware,
    ErrorHandlingMiddleware,
    LatencyLoggingMiddleware,
    LLMTokenLoggingMiddleware,
    RequestIDMiddleware,
)
from app.api.v1 import auth, dashboard, projects, review_queue, integrations, webhooks, notifications, audit_logs

settings = get_settings()
log = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title='ParaWorks API',
        version='1.0.0',
        docs_url='/api/docs' if settings.APP_ENV != 'production' else None,
        redoc_url='/api/redoc' if settings.APP_ENV != 'production' else None,
    )

    # ── Middleware (outer → inner, i.e. last added = outermost) ──────────────
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LatencyLoggingMiddleware)
    app.add_middleware(LLMTokenLoggingMiddleware)
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # ── API Routers ───────────────────────────────────────────────────────────
    prefix = '/api/v1'
    app.include_router(auth.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(review_queue.router, prefix=prefix)
    app.include_router(integrations.router, prefix=prefix)
    app.include_router(webhooks.router, prefix=prefix)
    app.include_router(notifications.router, prefix=prefix)
    app.include_router(audit_logs.router, prefix=prefix)

    @app.get('/health')
    async def health() -> dict:
        return {'status': 'ok'}

    return app


app = create_app()
