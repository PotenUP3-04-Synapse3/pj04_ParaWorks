from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.core.rbac import ensure_can_review_permission
from backend.app.db.session import get_db
from backend.app.knowledge.promotion import (
    build_promotion_preview,
    promote_review_item,
    validate_review_item_for_approval,
)
from backend.app.models import AgentRun, ReviewItem
from backend.app.schemas.review import ReviewEvidenceRequest, ReviewItemUpdate
from backend.app.services.audit import record_audit_log

router = APIRouter(prefix='/review', tags=['review'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


def _review_item_response(item: ReviewItem, agent_run: AgentRun | None = None) -> dict:
    agent_run_id = _agent_run_id(item)
    return {
        'id': item.id,
        'item_type': item.item_type,
        'payload': item.payload,
        'source_links': item.source_links,
        'source_snippets': item.source_snippets,
        'source_evidence': _source_evidence_response(item, agent_run),
        'agent_run_id': agent_run_id,
        'confidence_score': item.confidence_score,
        'permission_level': item.permission_level,
        'status': item.status,
        'reviewer_id': item.reviewer_id,
    }


@router.get('')
def list_review_items(db: DbSession, status: str = 'pending_review') -> dict[str, list[dict]]:
    items = db.scalars(
        select(ReviewItem).where(ReviewItem.status == status).order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc())
    ).all()
    agent_runs = _agent_runs_by_id(db, items)
    return {'items': [_review_item_response(item, agent_runs.get(_agent_run_id(item) or -1)) for item in items]}


@router.post('/approve-agent-candidates')
def approve_agent_review_candidates(
    db: DbSession,
    user: CurrentUser,
) -> dict:
    pending_items = db.scalars(
        select(ReviewItem).where(ReviewItem.status == 'pending_review').order_by(ReviewItem.id)
    ).all()
    approved_item_ids: list[int] = []
    skipped_count = 0

    for item in pending_items:
        if not _is_agent_candidate(item):
            skipped_count += 1
            continue
        if not item.source_links or not item.source_snippets:
            skipped_count += 1
            continue
        try:
            ensure_can_review_permission(user, item.permission_level)
            validate_review_item_for_approval(item)
        except (HTTPException, ValueError):
            skipped_count += 1
            continue

        item.status = 'approved'
        item.reviewer_id = user.id
        item.reviewed_at = datetime.now(UTC)
        promote_review_item(db, item)
        approved_item_ids.append(item.id)

    record_audit_log(
        db=db,
        actor=user,
        action='review.approve_agent_candidates',
        target_type='review_queue',
        target_id='agent_candidates',
        metadata={
            'approved_count': len(approved_item_ids),
            'skipped_count': skipped_count,
            'approved_item_ids': approved_item_ids,
        },
    )
    db.commit()

    return {
        'approved_count': len(approved_item_ids),
        'skipped_count': skipped_count,
        'approved_item_ids': approved_item_ids,
        'cost_policy': {
            'paid_llm_calls': False,
            'embedding_calls': False,
            'requires_human_review_state': True,
        },
    }


@router.patch('/{item_id}')
def update_review_item(
    item_id: int,
    update: ReviewItemUpdate,
    db: DbSession,
) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Review item not found')

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return _review_item_response(item, _agent_run_for_item(db, item))


def _is_agent_candidate(item: ReviewItem) -> bool:
    return isinstance(item.payload.get('agent_name'), str)


@router.get('/{item_id}/promotion-preview')
def preview_review_item_promotion(item_id: int, db: DbSession) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Review item not found')
    return build_promotion_preview(item)


@router.post('/{item_id}/approve')
def approve_review_item(
    item_id: int,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Review item not found')
    if not item.source_links or not item.source_snippets:
        raise HTTPException(status_code=400, detail='Review item requires source evidence')
    ensure_can_review_permission(user, item.permission_level)
    try:
        validate_review_item_for_approval(item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    item.status = 'approved'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.now(UTC)
    promote_review_item(db, item)
    record_audit_log(
        db=db,
        actor=user,
        action='review.approve',
        target_type='review_item',
        target_id=item.id,
        metadata={
            'item_type': item.item_type,
            'permission_level': item.permission_level,
        },
    )
    db.commit()
    db.refresh(item)
    return _review_item_response(item, _agent_run_for_item(db, item))


@router.post('/{item_id}/request-more-evidence')
def request_more_evidence_for_review_item(
    item_id: int,
    db: DbSession,
    user: CurrentUser,
    request: ReviewEvidenceRequest | None = None,
) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Review item not found')

    item.status = 'needs_more_evidence'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.now(UTC)
    note = (request.note or '').strip() if request else ''
    item.payload['needs_more_evidence'] = {
        'requested_at': item.reviewed_at.isoformat(),
        'requested_by': user.id,
        'note': note,
        'source_count': len(item.source_snippets or []),
        'previous_status': 'pending_review',
    }
    record_audit_log(
        db=db,
        actor=user,
        action='review.request_more_evidence',
        target_type='review_item',
        target_id=item.id,
        metadata={
            'item_type': item.item_type,
            'note_present': bool(note),
            'source_count': len(item.source_snippets or []),
        },
    )
    db.commit()
    db.refresh(item)
    return _review_item_response(item, _agent_run_for_item(db, item))


@router.post('/{item_id}/reject')
def reject_review_item(
    item_id: int,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Review item not found')

    item.status = 'rejected'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.now(UTC)
    record_audit_log(
        db=db,
        actor=user,
        action='review.reject',
        target_type='review_item',
        target_id=item.id,
        metadata={'item_type': item.item_type},
    )
    db.commit()
    db.refresh(item)
    return _review_item_response(item, _agent_run_for_item(db, item))


def _agent_run_id(item: ReviewItem) -> int | None:
    raw_id = item.payload.get('agent_run_id')
    if isinstance(raw_id, int):
        return raw_id
    if isinstance(raw_id, str) and raw_id.isdecimal():
        return int(raw_id)
    return None


def _agent_run_for_item(db: Session, item: ReviewItem) -> AgentRun | None:
    agent_run_id = _agent_run_id(item)
    if agent_run_id is None:
        return None
    return db.get(AgentRun, agent_run_id)


def _agent_runs_by_id(db: Session, items: list[ReviewItem]) -> dict[int, AgentRun]:
    agent_run_ids = sorted({agent_run_id for item in items if (agent_run_id := _agent_run_id(item)) is not None})
    if not agent_run_ids:
        return {}
    runs = db.scalars(select(AgentRun).where(AgentRun.id.in_(agent_run_ids))).all()
    return {run.id: run for run in runs}


def _source_evidence_response(item: ReviewItem, agent_run: AgentRun | None) -> list[dict]:
    evidence_summary = _agent_evidence_summary_by_url(agent_run)
    links = item.source_links or []
    snippets = item.source_snippets or []
    evidence_count = max(len(links), len(snippets))
    agent_run_id = _agent_run_id(item)
    rows: list[dict] = []

    for index in range(evidence_count):
        source_url = links[index] if index < len(links) else None
        source_snippet = snippets[index] if index < len(snippets) else ''
        summary = evidence_summary.get(source_url or '') or {}
        rows.append(
            {
                'index': index + 1,
                'rank': _int_or_default(summary.get('rank'), index + 1),
                'source_id': summary.get('source_id'),
                'source_url': source_url,
                'source_snippet': source_snippet,
                'permission_level': summary.get('permission_level') or item.permission_level,
                'confidence_score': item.confidence_score,
                'importance_score': _int_or_default(summary.get('importance_score'), 0),
                'timestamp': summary.get('timestamp'),
                'author': summary.get('author'),
                'agent_run_id': agent_run_id,
            }
        )

    return rows


def _agent_evidence_summary_by_url(agent_run: AgentRun | None) -> dict[str, dict]:
    if agent_run is None:
        return {}
    raw_summary = (agent_run.metadata_ or {}).get('evidence_summary')
    if not isinstance(raw_summary, list):
        return {}
    result: dict[str, dict] = {}
    for row in raw_summary:
        if not isinstance(row, dict):
            continue
        source_url = row.get('source_url')
        if isinstance(source_url, str):
            result[source_url] = row
    return result


def _int_or_default(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default
