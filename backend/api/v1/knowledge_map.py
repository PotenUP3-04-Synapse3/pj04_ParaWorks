from __future__ import annotations

"""지식 맵 API — React Flow 형식 노드/엣지 반환."""

from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.core.dependencies import CurrentUserId, DbSession

router = APIRouter(prefix='/knowledge-map', tags=['knowledge-map'])


@router.get('')
async def get_knowledge_map(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    depth: int = Query(2, ge=1, le=4),
):
    """노드(의사결정·지식자산·문서)와 엣지(참조·연관) 반환."""
    nodes = []
    edges = []
    seen_edges: set[str] = set()

    # 의사결정 노드
    dec_rows = (await db.execute(
        text(
            "SELECT id, title, confidence_score, review_status, permission_level "
            "FROM decision_records WHERE organization_id = :org_id LIMIT 100"
        ),
        {'org_id': org_id},
    )).fetchall()

    for r in dec_rows:
        nodes.append({
            'id': r[0],
            'type': 'decision',
            'data': {
                'label': r[1],
                'confidence_score': float(r[2]) if r[2] else None,
                'review_status': r[3],
                'permission_level': r[4],
            },
            'position': {'x': 0, 'y': 0},  # 클라이언트에서 자동 레이아웃
        })

    # 지식자산 노드
    ka_rows = (await db.execute(
        text(
            "SELECT id, title, asset_type, freshness_score "
            "FROM knowledge_assets WHERE organization_id = :org_id LIMIT 100"
        ),
        {'org_id': org_id},
    )).fetchall()

    for r in ka_rows:
        nodes.append({
            'id': r[0],
            'type': 'knowledge_asset',
            'data': {
                'label': r[1],
                'asset_type': r[2],
                'freshness_score': float(r[3]) if r[3] else None,
            },
            'position': {'x': 0, 'y': 0},
        })

    # 문서 컬렉션 노드 (최근 50개)
    doc_rows = (await db.execute(
        text(
            "SELECT id, title, source_type FROM document_collections "
            "WHERE organization_id = :org_id ORDER BY created_at DESC LIMIT 50"
        ),
        {'org_id': org_id},
    )).fetchall()

    for r in doc_rows:
        nodes.append({
            'id': r[0],
            'type': 'document',
            'data': {'label': r[1], 'source_type': r[2]},
            'position': {'x': 0, 'y': 0},
        })

    # 엣지 — 의사결정 ↔ 지식자산 (related_decisions 배열 참조)
    ka_link_rows = (await db.execute(
        text(
            "SELECT id, related_decisions FROM knowledge_assets "
            "WHERE organization_id = :org_id AND related_decisions IS NOT NULL"
        ),
        {'org_id': org_id},
    )).fetchall()

    for r in ka_link_rows:
        ka_id = r[0]
        related = r[1] or []
        for dec_id in related:
            edge_key = f'{ka_id}->{dec_id}'
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    'id': edge_key,
                    'source': ka_id,
                    'target': dec_id,
                    'type': 'reference',
                })

    return {'nodes': nodes, 'edges': edges}
