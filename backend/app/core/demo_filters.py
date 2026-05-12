from collections.abc import Iterable

from backend.app.models import ReviewItem


def _is_mock_source_link(link: str) -> bool:
    return ".mock/" in link


def filter_review_items(review_items: Iterable[ReviewItem]) -> list[ReviewItem]:
    return [
        item
        for item in review_items
        if not any(_is_mock_source_link(link) for link in (item.source_links or []))
    ]
