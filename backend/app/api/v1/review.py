from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.core.demo_filters import filter_review_items
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
AppSettings = Annotated[Settings, Depends(get_settings)]


def _review_item_response(item: ReviewItem, agent_run: AgentRun | None = None) -> dict:
    agent_run_id = _agent_run_id(item)
    
    # 에이전트 실행 상세 정보 추출
    agent_details = {
        'model_name': 'Unknown',
        'prompt_version': 'Unknown',
        'estimated_cost_usd': 0.0,
        'total_tokens': 0,
    }
    
    if agent_run:
        agent_details.update({
            'model_name': agent_run.model_name or 'gpt-4o-mini',
            'prompt_version': agent_run.prompt_version or 'v1',
            'estimated_cost_usd': agent_run.estimated_cost_usd or 0.0,
            'total_tokens': agent_run.total_tokens or 0,
        })

    return {
        'id': item.id,
        'item_type': item.item_type,
        'payload': item.payload,
        'source_links': item.source_links,
        'source_snippets': item.source_snippets,
        'source_evidence': _source_evidence_response(item, agent_run),
        'agent_run_id': agent_run_id,
        'agent_run_details': agent_details, # 상세 정보 추가
        'confidence_score': item.confidence_score,
        'permission_level': item.permission_level,
        'status': item.status,
        'reviewer_id': item.reviewer_id,
    }


@router.get('')
def list_review_items(db: DbSession, status: str = 'pending_review') -> dict:
    items = db.scalars(
        select(ReviewItem).where(ReviewItem.status == status).order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc())
    ).all()

    agent_runs = _agent_runs_by_id(db, items)
    
    # 그룹화 로직
    groups: dict[str, dict] = {}
    for item in items:
        agent_run = agent_runs.get(_agent_run_id(item) or -1)
        resp_item = _review_item_response(item, agent_run)
        
        # 제목(title)과 타입(item_type)을 기준으로 그룹 키 생성
        title = item.payload.get('title', f'Review item {item.id}')
        group_key = f"{item.item_type}:{title}"
        
        if group_key not in groups:
            groups[group_key] = {
                'group_id': group_key,
                'title': title,
                'item_type': item.item_type,
                'status': item.status,
                'permission_level': item.permission_level,
                'items': [],
                'total_count': 0,
                'avg_confidence': 0.0,
            }
        
        groups[group_key]['items'].append(resp_item)
        groups[group_key]['total_count'] += 1
        groups[group_key]['avg_confidence'] += item.confidence_score

    # 평균 신뢰도 계산 및 리스트 변환
    result_groups = []
    for group in groups.values():
        if group['total_count'] > 0:
            group['avg_confidence'] /= group['total_count']
        result_groups.append(group)

    return {'groups': result_groups, 'items': [_review_item_response(item, agent_runs.get(_agent_run_id(item) or -1)) for item in items]}


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

    # URL 정규화 맵 생성 (매칭 성공률을 높이기 위해)
    norm_summary = {}
    for url, info in evidence_summary.items():
        norm_url = _normalize_slack_url(url)
        if norm_url:
            norm_summary[norm_url] = info

    for index in range(evidence_count):
        source_url = links[index] if index < len(links) else None
        
        # snippets가 links보다 부족할 경우 처리
        if index < len(snippets):
            source_snippet = snippets[index]
        else:
            source_snippet = snippets[-1] if snippets else '원문 발췌 내용이 없습니다.'
            
        # 1순위: URL 직접 매칭
        summary = evidence_summary.get(source_url or '')
        
        # 2순위: 정규화된 URL 매칭 (슬랙 TS 형식 차이 극복)
        if not summary and source_url:
            norm_link = _normalize_slack_url(source_url)
            if norm_link:
                summary = norm_summary.get(norm_link)
        
        summary = summary or {}
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


def _normalize_slack_url(url: str | None) -> str | None:
    """슬랙 URL에서 타임스탬프 부분을 추출하여 정규화합니다."""
    if not url or '/p' not in url:
        return None
    
    # p 뒤의 숫자만 추출하여 뒤의 0을 제거 (예: p1715000123000000 -> 1715000123)
    ts_part = url.split('/p')[-1].split('?')[0]
    return ts_part.rstrip('0')


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
