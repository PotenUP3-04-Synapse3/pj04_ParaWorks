def test_company_memory_orchestration_api_exposes_langgraph_status(client) -> None:
    response = client.get('/api/v1/orchestration/company-memory')

    assert response.status_code == 200
    payload = response.json()
    assert payload['backend'] == 'langgraph'
    assert payload['workflow_name'] == 'company_memory'
    assert payload['node_names'] == [
        'collect_evidence',
        'draft_review_candidates',
        'retrieve_company_memory',
        'answer_with_rag',
    ]
    assert 'collect_evidence' in payload['graph_mermaid']
    assert payload['cost_policy'] == {
        'delta_sync': True,
        'source_hash_skip': True,
        'evidence_token_budget': True,
        'paid_llm_calls_in_status_api': False,
    }


def test_company_memory_orchestration_api_runs_deterministic_dry_run(client) -> None:
    response = client.post(
        '/api/v1/orchestration/company-memory/dry-run',
        json={'objective': 'answer_from_company_memory', 'question': 'Redis queue state'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['backend'] == 'langgraph'
    assert payload['objective'] == 'answer_from_company_memory'
    assert payload['completed_nodes'] == [
        'collect_evidence',
        'draft_review_candidates',
        'retrieve_company_memory',
        'answer_with_rag',
    ]
    assert payload['outputs']['review_boundary'] == 'human_approval_required'
    assert payload['outputs']['token_budget_policy'] == 'delta_sync_hash_skip_evidence_budget'
    assert payload['token_cost_usd'] == 0
