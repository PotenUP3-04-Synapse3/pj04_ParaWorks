from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.knowledge.promotion import promote_review_item
from backend.app.models import ReviewItem
from backend.app.schemas.review import ReviewItemUpdate

router = APIRouter(prefix='/review', tags=['review'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


def _review_item_response(item: ReviewItem) -> dict:
    return {
        'id': item.id,
        'item_type': item.item_type,
        'payload': item.payload,
        'source_links': item.source_links,
        'source_snippets': item.source_snippets,
        'confidence_score': item.confidence_score,
        'permission_level': item.permission_level,
        'status': item.status,
    }


@router.get('')
def list_review_items(db: DbSession, status: str = 'pending_review') -> dict[str, list[dict]]:
    items = db.scalars(
        select(ReviewItem).where(ReviewItem.status == status).order_by(ReviewItem.created_at.desc(), ReviewItem.id.desc())
    ).all()
    return {'items': [_review_item_response(item) for item in items]}


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
    return _review_item_response(item)


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

    item.status = 'approved'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.now(UTC)
    promote_review_item(db, item)
    db.commit()
    db.refresh(item)
    return _review_item_response(item)


@router.post('/{item_id}/request-more-evidence')
def request_more_evidence_for_review_item(
    item_id: int,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Review item not found')

    item.status = 'needs_more_evidence'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return _review_item_response(item)


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
    db.commit()
    db.refresh(item)
    return _review_item_response(item)
