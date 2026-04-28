from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import select, text

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.decision_record import DecisionRecord
from backend.models.document import DocumentCollection, DocumentVersion

router = APIRouter(prefix='/timeline', tags=['timeline'])


@router.get('')
async def get_timeline(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    source_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """조직 타임라인 이벤트 집계 (문서 + 의사결정)."""
    events: list[dict] = []

    # 문서 버전 이벤트
    doc_q = (
        select(
            DocumentCollection.id,
            DocumentCollection.title,
            DocumentCollection.source_type,
            DocumentCollection.source_url,
            DocumentVersion.created_at,
        )
        .join(DocumentVersion, DocumentVersion.collection_id == DocumentCollection.id)
        .where(DocumentCollection.organization_id == org_id)
    )
    if source_type:
        doc_q = doc_q.where(DocumentCollection.source_type == source_type)
    if from_date:
        doc_q = doc_q.where(DocumentVersion.created_at >= from_date)
    if to_date:
        doc_q = doc_q.where(DocumentVersion.created_at <= to_date)
    doc_q = doc_q.order_by(DocumentVersion.created_at.desc()).limit(limit)

    doc_rows = (await db.execute(doc_q)).fetchall()
    for row in doc_rows:
        events.append({
            'event_type': 'document',
            'id': row[0],
            'title': row[1],
            'source_type': row[2],
            'source_url': row[3],
            'occurred_at': row[4].isoformat() if row[4] else None,
        })

    # 의사결정 이벤트
    dec_q = (
        select(
            DecisionRecord.id,
            DecisionRecord.title,
            DecisionRecord.decision_summary,
            DecisionRecord.decided_at,
        )
        .where(DecisionRecord.organization_id == org_id)
    )
    if from_date:
        dec_q = dec_q.where(DecisionRecord.decided_at >= from_date)
    if to_date:
        dec_q = dec_q.where(DecisionRecord.decided_at <= to_date)
    dec_q = dec_q.order_by(DecisionRecord.decided_at.desc()).limit(limit)

    dec_rows = (await db.execute(dec_q)).fetchall()
    for row in dec_rows:
        events.append({
            'event_type': 'decision',
            'id': row[0],
            'title': row[1],
            'summary': row[2],
            'source_type': 'decision',
            'source_url': None,
            'occurred_at': row[3].isoformat() if row[3] else None,
        })

    # 최신순 정렬
    events.sort(key=lambda e: e['occurred_at'] or '', reverse=True)
    return events[:limit]
