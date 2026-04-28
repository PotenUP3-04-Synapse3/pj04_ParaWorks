from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.dependencies import CurrentUserId, DbSession
from backend.core.permissions import PermissionResolver
from backend.schemas.search import SearchRequest, SearchResponse
from backend.agents import search as run_search
from backend.models.user import User
from sqlalchemy import select

router = APIRouter(prefix='/search', tags=['search'])


@router.post('', response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: DbSession,
    user_id: CurrentUserId,
) -> SearchResponse:
    """자연어 쿼리로 전사 지식 검색."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    resolver = PermissionResolver(role=user.role)
    accessible_levels = resolver.accessible_levels()

    result = await run_search(
        query=request.query,
        organization_id=request.org_id,
        user_id=user_id,
        accessible_permission_levels=accessible_levels,
    )
    return result
