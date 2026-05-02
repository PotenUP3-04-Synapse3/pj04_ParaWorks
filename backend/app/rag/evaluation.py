from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    hit_rate: float
    expected_count: int
    retrieved_count: int
    matched_expected_source_ids: list[str]


def evaluate_retrieval_matches(
    *,
    expected_source_ids: Iterable[str],
    retrieved_source_ids: Sequence[str],
    k: int,
) -> RetrievalMetrics:
    expected = set(expected_source_ids)
    top_k = list(retrieved_source_ids[:k])
    matched = [source_id for source_id in top_k if source_id in expected]
    precision_denominator = len(top_k) or 1
    recall_denominator = len(expected) or 1
    return RetrievalMetrics(
        precision_at_k=round(len(matched) / precision_denominator, 6),
        recall_at_k=round(len(set(matched)) / recall_denominator, 6),
        hit_rate=1.0 if matched else 0.0,
        expected_count=len(expected),
        retrieved_count=len(top_k),
        matched_expected_source_ids=matched,
    )
