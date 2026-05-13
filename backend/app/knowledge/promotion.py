from sqlalchemy.orm import Session

from backend.app.models import DecisionRecord, HistoryEvent, ReviewItem, TimelineEvent, Todo


PROMOTABLE_REVIEW_TYPES = {'decision_record', 'history_event', 'timeline_event', 'todo'}


def build_promotion_preview(item: ReviewItem) -> dict:
    normalized_payload = _normalized_payload_for_item(item)
    missing_required_fields = [
        field
        for field, value in normalized_payload.items()
        if field in _required_fields_for_type(item.item_type) and not str(value).strip()
    ]

    return {
        'target_type': item.item_type if item.item_type in PROMOTABLE_REVIEW_TYPES else 'review_item',
        'can_approve': not missing_required_fields,
        'missing_required_fields': missing_required_fields,
        'normalized_payload': normalized_payload,
    }


def validate_review_item_for_approval(item: ReviewItem) -> None:
    preview = build_promotion_preview(item)
    if not preview['can_approve']:
        raise ValueError('Review item is missing required fields')


def promote_review_item(db: Session, item: ReviewItem) -> None:
    validate_review_item_for_approval(item)
    normalized = _normalized_payload_for_item(item)
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
                title=normalized['title'],
                decision_summary=normalized['decision_summary'],
                **base_fields,
            )
        )
        db.add(
            TimelineEvent(
                title=f"[寃곗젙] {normalized['title']}",
                result_summary=normalized['decision_summary'],
                **base_fields,
            )
        )
        return

    if item.item_type == 'history_event':
        db.add(
            HistoryEvent(
                title=normalized['title'],
                reason=normalized['reason'],
                **base_fields,
            )
        )
        db.add(
            TimelineEvent(
                title=normalized['title'],
                result_summary=normalized['reason'],
                **base_fields,
            )
        )
        return

    if item.item_type == 'timeline_event':
        db.add(
            TimelineEvent(
                title=normalized['title'],
                result_summary=normalized['result_summary'],
                **base_fields,
            )
        )
        return

    if item.item_type == 'todo':
        db.add(
            Todo(
                title=normalized['title'],
                priority=normalized['priority'],
                priority_reason=normalized['priority_reason'],
                **base_fields,
            )
        )
        db.add(
            TimelineEvent(
                title=f"[???? {normalized['title']}",
                result_summary=(
                    f"?대떦?? {item.payload.get('assignee', '誘몄젙')}, "
                    f"湲고븳: {item.payload.get('due_date', '湲고븳 ?놁쓬')}"
                ),
                **base_fields,
            )
        )


def _normalized_payload_for_item(item: ReviewItem) -> dict[str, str]:
    if item.item_type == 'decision_record':
        return {
            'title': _string_payload(item, 'title'),
            'decision_summary': _string_payload(item, 'decision_summary') or _string_payload(item, 'summary'),
        }

    if item.item_type == 'history_event':
        return {
            'title': _string_payload(item, 'title'),
            'reason': _string_payload(item, 'reason') or _string_payload(item, 'summary'),
        }

    if item.item_type == 'timeline_event':
        return {
            'title': _string_payload(item, 'title'),
            'result_summary': (
                _string_payload(item, 'result_summary')
                or _string_payload(item, 'summary')
                or _string_payload(item, 'reason')
            ),
        }

    if item.item_type == 'todo':
        return {
            'title': _string_payload(item, 'title'),
            'priority': _string_payload(item, 'priority') or 'medium',
            'priority_reason': _string_payload(item, 'priority_reason') or _string_payload(item, 'summary'),
        }

    return {
        'title': _string_payload(item, 'title'),
        'summary': _string_payload(item, 'summary'),
    }


def _required_fields_for_type(item_type: str) -> tuple[str, ...]:
    if item_type == 'decision_record':
        return ('title', 'decision_summary')
    if item_type == 'history_event':
        return ('title', 'reason')
    if item_type == 'timeline_event':
        return ('title', 'result_summary')
    if item_type == 'todo':
        return ('title', 'priority', 'priority_reason')
    return ()


def _string_payload(item: ReviewItem, key: str) -> str:
    value = item.payload.get(key)
    return value if isinstance(value, str) else ''
