"""Dashboard route — project summary for the authenticated user."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.todo import Todo, TodoStatus
from app.models.review_item import ReviewItem, ReviewItemStatus

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    pending_reviews: int
    total_approved_todos: int


class RecentProjectSummary(BaseModel):
    id: UUID
    name: str
    status: str
    risk_level: Optional[str]
    todo_count: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_projects: List[RecentProjectSummary]


@router.get('', response_model=DashboardResponse)
async def get_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id

    total = await db.scalar(select(func.count(Project.id)).where(Project.organization_id == org_id))
    active = await db.scalar(
        select(func.count(Project.id)).where(
            Project.organization_id == org_id,
            Project.status == ProjectStatus.active,
        )
    )
    pending = await db.scalar(
        select(func.count(ReviewItem.id)).where(
            ReviewItem.organization_id == org_id,
            ReviewItem.status == ReviewItemStatus.draft,
        )
    )
    approved_todos = await db.scalar(
        select(func.count(Todo.id)).where(
            Todo.status == TodoStatus.approved,
        )
    )

    projects_result = await db.execute(
        select(Project)
        .where(Project.organization_id == org_id)
        .order_by(Project.updated_at.desc())
        .limit(5)
    )
    projects = projects_result.scalars().all()

    recent = []
    for p in projects:
        todo_count = await db.scalar(
            select(func.count(Todo.id)).where(
                Todo.project_id == p.id,
                Todo.status == TodoStatus.approved,
            )
        ) or 0
        recent.append(
            RecentProjectSummary(
                id=p.id,
                name=p.name,
                status=p.status.value,
                risk_level=p.risk_level.value if p.risk_level else None,
                todo_count=todo_count,
            )
        )

    return DashboardResponse(
        stats=DashboardStats(
            total_projects=total or 0,
            active_projects=active or 0,
            pending_reviews=pending or 0,
            total_approved_todos=approved_todos or 0,
        ),
        recent_projects=recent,
    )
