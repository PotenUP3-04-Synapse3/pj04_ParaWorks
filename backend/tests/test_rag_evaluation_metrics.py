import json
from pathlib import Path

from backend.app.agents.rag_orchestrator_agent.service import (
    retrieve_matching_evidence_candidates,
)
from backend.app.rag.evaluation import evaluate_retrieval_matches
from backend.tests.test_rag_quality import seed_chunk

FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'rag_smoke_eval_cases.json'


def test_retrieval_metrics_report_precision_recall_and_hits() -> None:
    metrics = evaluate_retrieval_matches(
        expected_source_ids={'gmail-1', 'slack-1'},
        retrieved_source_ids=['slack-1', 'drive-1'],
        k=2,
    )

    assert metrics.precision_at_k == 0.5
    assert metrics.recall_at_k == 0.5
    assert metrics.hit_rate == 1.0
    assert metrics.expected_count == 2
    assert metrics.retrieved_count == 2
    assert metrics.matched_expected_source_ids == ['slack-1']


def test_rag_smoke_fixture_meets_precision_recall_floor(db_session) -> None:
    case = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))['cases'][0]
    for chunk in case['chunks']:
        seed_chunk(
            db_session,
            source_type=chunk['source_type'],
            source_id=chunk['source_id'],
            title=chunk['title'],
            text=chunk['text'],
        )

    candidates = retrieve_matching_evidence_candidates(db=db_session, question=case['query'])
    metrics = evaluate_retrieval_matches(
        expected_source_ids=set(case['expected_source_ids']),
        retrieved_source_ids=[candidate.source_id for candidate in candidates],
        k=case['k'],
    )

    assert metrics.precision_at_k >= 0.66
    assert metrics.recall_at_k == 1.0
    assert metrics.hit_rate == 1.0
