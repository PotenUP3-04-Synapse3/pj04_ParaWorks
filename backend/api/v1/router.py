from fastapi import APIRouter

from backend.api.v1.auth import router as auth_router
from backend.api.v1.search import router as search_router
from backend.api.v1.decisions import router as decisions_router
from backend.api.v1.knowledge import router as knowledge_router
from backend.api.v1.timeline import router as timeline_router
from backend.api.v1.sources import router as sources_router
from backend.api.v1.projects import router as projects_router
from backend.api.v1.review import router as review_router
from backend.api.v1.notifications import router as notifications_router
from backend.api.v1.integrations import router as integrations_router
from backend.api.v1.admin import router as admin_router
from backend.api.v1.knowledge_map import router as knowledge_map_router
from backend.api.v1.stream import router as stream_router

router = APIRouter(prefix='/api/v1')
router.include_router(auth_router)
router.include_router(search_router)
router.include_router(decisions_router)
router.include_router(knowledge_router)
router.include_router(timeline_router)
router.include_router(sources_router)
router.include_router(projects_router)
router.include_router(review_router)
router.include_router(notifications_router)
router.include_router(integrations_router)
router.include_router(admin_router)
router.include_router(knowledge_map_router)
router.include_router(stream_router)
