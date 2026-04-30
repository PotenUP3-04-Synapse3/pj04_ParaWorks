"""Knowledge Map API — returns project/decision/source relationships as graph nodes & edges."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.decision_record import DecisionRecord, DecisionReviewStatus
from app.models.history import HistoryEvent, HistoryStatus
from app.models.project import Project, ProjectStatus
from app.models.similar_case import SimilarCase

router = APIRouter(prefix='/knowledge-map', tags=['knowledge-map'])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ──────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str  # "project" | "decision" | "history"
    data: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str   # "has_decision" | "has_history" | "similar_to"
    label: Optional[str] = None


class KnowledgeMapResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int


# ── Endpoint ──────────────────────────────────────────────────────────────

@router.get('', response_model=KnowledgeMapResponse)
async def get_knowledge_map(
    request: Request,
    db: AsyncSession = Depends(get_db),
    project_id: Optional[UUID] = Query(None, description='Filter to a specific project'),
    include_history: bool = Query(True),
    include_decisions: bool = Query(True),
    include_similar: bool = Query(True),
    limit_projects: int = Query(20, ge=1, le=100),
) -> KnowledgeMapResponse:
    """
    Return organizational knowledge as a graph (React Flow compatible format).

    Nodes: Projects, DecisionRecords, HistoryEvents
    Edges: project→decision (has_decision), project→history (has_history), similar cases
    """
    org_id = request.state.org_id

    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    # ── Projects ──────────────────────────────────────────────────────────
    project_q = (
        select(Project)
        .where(Project.organization_id == org_id)
        .order_by(Project.created_at.desc())
        .limit(limit_projects)
    )
    if project_id:
        project_q = project_q.where(Project.id == project_id)

    projects = (await db.execute(project_q)).scalars().all()
    project_ids = [p.id for p in projects]

    for p in projects:
        nodes.append(
            GraphNode(
                id=f'project:{p.id}',
                label=p.name,
                node_type='project',
                data={
                    'status': p.status.value if p.status else None,
                    'risk_level': p.risk_level.value if p.risk_level else None,
                    'description': (p.description or '')[:200],
                },
            )
        )

    # ── DecisionRecords ───────────────────────────────────────────────────
    if include_decisions and project_ids:
        dec_q = select(DecisionRecord).where(
            DecisionRecord.organization_id == org_id,
            DecisionRecord.review_status == DecisionReviewStatus.approved,
        )
        if project_id:
            dec_q = dec_q.where(DecisionRecord.related_project_id == project_id)

        decisions = (await db.execute(dec_q)).scalars().all()

        for d in decisions:
            nodes.append(
                GraphNode(
                    id=f'decision:{d.id}',
                    label=d.title,
                    node_type='decision',
                    data={
                        'summary': (d.decision_summary or '')[:200],
                        'business_domain': d.business_domain,
                        'decided_at': d.decided_at.isoformat() if d.decided_at else None,
                        'confidence_score': d.confidence_score,
                    },
                )
            )
            if d.related_project_id:
                edges.append(
                    GraphEdge(
                        id=f'edge:proj-dec:{d.related_project_id}:{d.id}',
                        source=f'project:{d.related_project_id}',
                        target=f'decision:{d.id}',
                        edge_type='has_decision',
                        label='결정',
                    )
                )

    # ── HistoryEvents ─────────────────────────────────────────────────────
    if include_history and project_ids:
        hist_q = select(HistoryEvent).where(
            HistoryEvent.project_id.in_(project_ids),
            HistoryEvent.status == HistoryStatus.approved,
        )
        histories = (await db.execute(hist_q)).scalars().all()

        for h in histories:
            nodes.append(
                GraphNode(
                    id=f'history:{h.id}',
                    label=h.title,
                    node_type='history',
                    data={
                        'decision': (h.decision or '')[:200],
                        'decision_maker': h.decision_maker,
                        'event_time': h.event_time.isoformat() if h.event_time else None,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    id=f'edge:proj-hist:{h.project_id}:{h.id}',
                    source=f'project:{h.project_id}',
                    target=f'history:{h.id}',
                    edge_type='has_history',
                    label='히스토리',
                )
            )

    # ── SimilarCases edges ────────────────────────────────────────────────
    if include_similar:
        sc_q = select(SimilarCase).where(SimilarCase.organization_id == org_id)
        similar_cases = (await db.execute(sc_q)).scalars().all()

        for sc in similar_cases:
            src_id = None
            tgt_id = None
            if sc.source_history_id:
                src_id = f'history:{sc.source_history_id}'
            elif sc.source_decision_id:
                src_id = f'decision:{sc.source_decision_id}'
            if sc.target_history_id:
                tgt_id = f'history:{sc.target_history_id}'
            elif sc.target_decision_id:
                tgt_id = f'decision:{sc.target_decision_id}'

            if src_id and tgt_id:
                edges.append(
                    GraphEdge(
                        id=f'edge:similar:{sc.id}',
                        source=src_id,
                        target=tgt_id,
                        edge_type='similar_to',
                        label=f'유사 {sc.similarity_score:.0%}',
                    )
                )

    return KnowledgeMapResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
    )
