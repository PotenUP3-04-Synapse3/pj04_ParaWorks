from sqlalchemy.orm import Session

from backend.app.models import DecisionRecord, HistoryEvent, ReviewItem, Todo


def promote_review_item(db: Session, item: ReviewItem) -> None:
    base_fields = {
        'source_links': item.source_links,
        'source_snippets': item.source_snippets,
        'confidence_score': item.confidence_score,
        'permission_level': item.permission_level,
        'review_status': 'approved',
    }

    if item.item_type == 'decision_record':
        db.add(
            DecisionRecord(
                title=str(item.payload.get('title', 'Untitled decision')),
                decision_summary=str(item.payload.get('decision_summary') or item.payload.get('summary') or ''),
                **base_fields,
            )
        )
        return

    if item.item_type == 'history_event':
        db.add(
            HistoryEvent(
                title=str(item.payload.get('title', 'Untitled history event')),
                reason=str(item.payload.get('reason') or item.payload.get('summary') or ''),
                **base_fields,
            )
        )
        return

    if item.item_type == 'todo':
        db.add(
            Todo(
                title=str(item.payload.get('title', 'Untitled todo')),
                priority=str(item.payload.get('priority', 'medium')),
                priority_reason=str(item.payload.get('priority_reason') or item.payload.get('summary') or ''),
                **base_fields,
            )
        )
