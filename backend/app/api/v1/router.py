from fastapi import APIRouter

from backend.app.api.v1 import (
    admin,
    agent_runs,
    ask,
    auth,
    dashboard,
    integrations,
    knowledge,
    messages,
    orchestration,
    rag,
    review,
    search,
    stream,
)

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(admin.router)
api_router.include_router(agent_runs.router)
api_router.include_router(ask.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(integrations.router)
api_router.include_router(knowledge.router)
api_router.include_router(messages.router)
api_router.include_router(orchestration.router)
api_router.include_router(rag.router)
api_router.include_router(review.router)
api_router.include_router(search.router)
api_router.include_router(stream.router)
