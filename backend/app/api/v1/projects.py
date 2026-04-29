"""Projects, Todos, Timeline, History routes."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project import Project, ProjectStatus, RiskLevel
from app.models.todo import Todo, TodoStatus, Priority
from app.models.timeline import TimelineEvent, EventStatus
from app.models.history import HistoryEvent, HistoryStatus

router = APIRouter(prefix='/projects', tags=['projects'])


# ── Pydantic schemas ──────────────────────────────────────────────────────

class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: str
    risk_level: Optional[str]

    model_config = {'from_attributes': True}


class TodoOut(BaseModel):
    id: UUID
    title: str
    assignee: Optional[str]
    due_date: Optional[str]
    priority: Optional[str]
    priority_score: Optional[float]
    status: str
    confidence_score: Optional[float]
    source_links: Optional[List[str]]

    model_config = {'from_attributes': True}


class TimelineEventOut(BaseModel):
    id: UUID
    title: str
    result_summary: Optional[str]
    event_time: Optional[str]
    status: str
    confidence_score: Optional[float]
    source_links: Optional[List[str]]

    model_config = {'from_attributes': True}


class HistoryEventOut(BaseModel):
    id: UUID
    title: str
    situation: Optional[str]
    decision: Optional[str]
    decision_maker: Optional[str]
    event_time: Optional[str]
    status: str
    confidence_score: Optional[float]
    source_links: Optional[List[str]]
    source_snippets: Optional[List[dict]]

    model_config = {'from_attributes': True}


# ── Projects ──────────────────────────────────────────────────────────────

@router.get('', response_model=List[ProjectOut])
async def list_projects(request: Request, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    result = await db.execute(
        select(Project).where(Project.organization_id == org_id).order_by(Project.updated_at.desc())
    )
    return result.scalars().all()


@router.get('/{project_id}', response_model=ProjectOut)
async def get_project(project_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


# ── Todos ─────────────────────────────────────────────────────────────────

@router.get('/{project_id}/todos', response_model=List[TodoOut])
async def list_todos(
    project_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
):
    query = select(Todo).where(Todo.project_id == project_id)
    if status:
        query = query.where(Todo.status == TodoStatus(status))
    result = await db.execute(query.order_by(Todo.priority_score.desc()))
    return result.scalars().all()


@router.patch('/{project_id}/todos/{todo_id}', response_model=TodoOut)
async def update_todo(
    project_id: UUID,
    todo_id: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.project_id == project_id)
    )
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail='Todo not found')

    for field in ('title', 'assignee', 'due_date', 'priority', 'status'):
        if field in body:
            setattr(todo, field, body[field])

    await db.commit()
    await db.refresh(todo)
    return todo


# ── Timeline ──────────────────────────────────────────────────────────────

@router.get('/{project_id}/timeline', response_model=List[TimelineEventOut])
async def get_timeline(
    project_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.project_id == project_id)
        .order_by(TimelineEvent.event_time.asc())
    )
    return result.scalars().all()


# ── History ───────────────────────────────────────────────────────────────

@router.get('/{project_id}/history', response_model=List[HistoryEventOut])
async def get_history(
    project_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HistoryEvent)
        .where(HistoryEvent.project_id == project_id)
        .order_by(HistoryEvent.event_time.desc())
    )
    return result.scalars().all()
