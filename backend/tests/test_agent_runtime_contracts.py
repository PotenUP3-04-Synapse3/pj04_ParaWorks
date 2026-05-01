from backend.app.agent_runtime import (
    AgentRunCost,
    EvidenceMessage,
    EvidencePacket,
    PermissionContext,
    ReviewCandidate,
    TokenUsage,
    build_evidence_cache_key,
    estimate_agent_run_cost,
    evaluate_agent_cost_budget,
)


def test_evidence_packet_keeps_strictest_permission() -> None:
    packet = EvidencePacket(
        source_type='slack',
        source_window='C123:2026-05-01',
        messages=[
            EvidenceMessage(
                source_id='C123:1',
                source_url='https://example.slack.com/archives/C123/p1',
                text='internal update',
                author='U1',
                timestamp='2026-05-01T09:00:00+09:00',
                permission_level='internal',
            ),
            EvidenceMessage(
                source_id='C123:2',
                source_url='https://example.slack.com/archives/C123/p2',
                text='restricted decision',
                author='U2',
                timestamp='2026-05-01T09:05:00+09:00',
                permission_level='restricted',
            ),
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )

    assert packet.strictest_permission == 'restricted'
    assert packet.source_links == [
        'https://example.slack.com/archives/C123/p1',
        'https://example.slack.com/archives/C123/p2',
    ]


def test_review_candidate_requires_evidence() -> None:
    candidate = ReviewCandidate(
        item_type='history_event',
        title='Redis decision discussed',
        summary='The team discussed queue architecture.',
        source_links=[],
        source_snippets=[],
        confidence_score=0.8,
        permission_level='internal',
    )

    try:
        candidate.validate_evidence()
    except ValueError as exc:
        assert str(exc) == 'review candidate requires source evidence'
    else:
        raise AssertionError('candidate without evidence should be rejected')


def test_evidence_cache_key_is_stable_and_prompt_versioned() -> None:
    packet = EvidencePacket(
        source_type='slack',
        source_window='C123:2026-05-01',
        messages=[
            EvidenceMessage(
                source_id='C123:1',
                source_url='https://example.slack.com/archives/C123/p1',
                text='launch review moved to Friday',
                author='U1',
                timestamp='2026-05-01T09:00:00+09:00',
                permission_level='internal',
            )
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )

    first = build_evidence_cache_key(packet, prompt_version='slack-timeline:v1')
    second = build_evidence_cache_key(packet, prompt_version='slack-timeline:v1')
    changed = build_evidence_cache_key(packet, prompt_version='slack-timeline:v2')

    assert first == second
    assert first != changed


def test_estimate_agent_run_cost_records_token_metadata() -> None:
    cost = estimate_agent_run_cost(
        model_name='gpt-test',
        token_usage=TokenUsage(input_tokens=1000, output_tokens=250),
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        cache_hit=False,
    )

    assert isinstance(cost, AgentRunCost)
    assert cost.model_name == 'gpt-test'
    assert cost.token_usage.total_tokens == 1250
    assert cost.estimated_cost_usd == 0.0003
    assert cost.cache_hit is False


def test_cost_budget_decision_skips_over_budget_run() -> None:
    decision = evaluate_agent_cost_budget(
        model_name='gpt-test',
        token_usage=TokenUsage(input_tokens=20_000, output_tokens=5_000),
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        max_cost_usd=0.001,
        cache_hit=False,
    )

    assert decision.action == 'skip'
    assert decision.reason == 'budget_exceeded'
    assert decision.budget_status == 'over_budget'
    assert decision.estimated_cost_usd == 0.006
    assert decision.budget_limit_usd == 0.001


def test_cost_budget_decision_uses_cache_before_budget_rejection() -> None:
    decision = evaluate_agent_cost_budget(
        model_name='gpt-test',
        token_usage=TokenUsage(input_tokens=20_000, output_tokens=5_000),
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        max_cost_usd=0.001,
        cache_hit=True,
    )

    assert decision.action == 'use_cache'
    assert decision.reason == 'cache_hit'
    assert decision.budget_status == 'cached'
    assert decision.estimated_cost_usd == 0.006
