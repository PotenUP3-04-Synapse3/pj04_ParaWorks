from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.database import init_db
from backend.api.v1.router import router as api_router

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('startup.begin')
    await init_db()
    log.info('startup.db_initialized')
    yield
    log.info('shutdown.begin')


app = FastAPI(
    title='ParaWorks',
    version='0.1.0',
    description='전사 지식·의사결정 이력 관리 플랫폼',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(',') if o.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)


@app.get('/health', tags=['ops'])
async def health() -> dict:
    return {'status': 'ok'}
