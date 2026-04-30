from fastapi import APIRouter

from backend.app.api.v1 import dashboard, integrations, review, search, stream

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(dashboard.router)
api_router.include_router(integrations.router)
api_router.include_router(review.router)
api_router.include_router(search.router)
api_router.include_router(stream.router)
