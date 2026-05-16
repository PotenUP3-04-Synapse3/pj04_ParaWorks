from backend.app.models import ReviewItem

LOW_SIGNAL_REVIEW_TITLES = {
    'paraworks source 연결',
    'source 연결',
    'untitled',
    'unknown',
}

DISPLAY_TITLE_KEYS = (
    'title',
    'summary',
    'decision_summary',
    'reason',
    'priority_reason',
    'task_summary',
    'source_title',
    'project_assignment_summary',
    'evidence_reason',
    'recommended_next_step',
)


def review_item_display_title(item: ReviewItem) -> str:
    return review_payload_display_title(item.payload, item.id)


def review_payload_display_title(payload: dict, item_id: int) -> str:
    title = _text_field(payload.get('title'))
    if title and not _is_low_signal_title(title):
        return title

    for key in DISPLAY_TITLE_KEYS[1:]:
        value = _text_field(payload.get(key))
        if value and not _is_low_signal_title(value):
            return _one_line(value)

    return f'Review item {item_id}'


def _text_field(value: object) -> str:
    return value.strip() if isinstance(value, str) else ''


def _one_line(value: str) -> str:
    return ' '.join(value.split())


def _is_low_signal_title(value: str) -> bool:
    normalized = _one_line(value).lower()
    return normalized in LOW_SIGNAL_REVIEW_TITLES or normalized.endswith(' source 연결')
