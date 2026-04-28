from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.decision_record import DecisionRecord
from backend.models.document import DocumentCollection, DocumentVersion
from backend.models.project import Project
from backend.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix='/projects', tags=['projects'])


@router.get('', response_model=list[ProjectRead])
async def list_projects(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(Project)
        .where(Project.organization_id == org_id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post('', response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: DbSession, user_id: CurrentUserId):
    project = Project(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get('/{project_id}', response_model=ProjectRead)
async def get_project(project_id: str, db: DbSession, user_id: CurrentUserId):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return project


@router.patch('/{project_id}', response_model=ProjectRead)
async def update_project(project_id: str, payload: ProjectUpdate, db: DbSession, user_id: CurrentUserId):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.get('/{project_id}/timeline')
async def project_timeline(
    project_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    source_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """프로젝트 타임라인 — 연관 의사결정 + 문서 버전."""
    from sqlalchemy import text

    params: dict = {'pid': project_id, 'lim': limit}

    # 의사결정 이벤트
    dec_rows = (await db.execute(
        text(
            "SELECT id, title, decision_summary, decided_at "
            "FROM decision_records "
            "WHERE related_project_id = :pid "
            "ORDER BY decided_at DESC LIMIT :lim"
        ),
        params,
    )).fetchall()

    events = [
        {
            'event_type': 'decision',
            'id': r[0],
            'title': r[1],
            'summary': r[2],
            'source_type': 'decision',
            'source_url': None,
            'occurred_at': r[3].isoformat() if r[3] else None,
        }
        for r in dec_rows
    ]

    # 문서 이벤트 (metadata에 project_id 저장된 경우)
    doc_rows = (await db.execute(
        text(
            "SELECT dc.id, dc.title, dc.source_type, dc.source_url, dv.created_at "
            "FROM document_collections dc "
            "JOIN document_versions dv ON dv.collection_id = dc.id "
            "WHERE dc.metadata->>'project_id' = :pid "
            "ORDER BY dv.created_at DESC LIMIT :lim"
        ),
        params,
    )).fetchall()

    events += [
        {
            'event_type': 'document',
            'id': r[0],
            'title': r[1],
            'source_type': r[2],
            'source_url': r[3],
            'occurred_at': r[4].isoformat() if r[4] else None,
        }
        for r in doc_rows
    ]

    events.sort(key=lambda e: e['occurred_at'] or '', reverse=True)
    return events[:limit]


@router.get('/{project_id}/history')
async def project_history(
    project_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    limit: int = Query(50, ge=1, le=200),
):
    """프로젝트 연관 문서 버전 변경 이력."""
    from sqlalchemy import text

    rows = (await db.execute(
        text(
            "SELECT dv.id, dv.version_label, dv.content_hash, dv.diff_from_previous, "
            "       dv.created_at, dc.title, dc.source_type "
            "FROM document_versions dv "
            "JOIN document_collections dc ON dv.collection_id = dc.id "
            "WHERE dc.metadata->>'project_id' = :pid "
            "ORDER BY dv.created_at DESC LIMIT :lim"
        ),
        {'pid': project_id, 'lim': limit},
    )).fetchall()

    return [
        {
            'version_id': r[0],
            'version_label': r[1],
            'content_hash': r[2],
            'diff': r[3],
            'occurred_at': r[4].isoformat() if r[4] else None,
            'document_title': r[5],
            'source_type': r[6],
        }
        for r in rows
    ]
