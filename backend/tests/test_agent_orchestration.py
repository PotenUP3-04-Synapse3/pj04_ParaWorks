from backend.app.agent_runtime.orchestration import (
    AgentWorkflowState,
    build_company_memory_workflow,
)


def test_company_memory_workflow_runs_nodes_in_langgraph_order() -> None:
    workflow = build_company_memory_workflow()

    result = workflow.run(
        AgentWorkflowState(
            objective='answer_from_company_memory',
            inputs={'question': 'Redis queue state'},
        )
    )

    assert workflow.backend == 'langgraph'
    assert workflow.node_names == [
        'collect_evidence',
        'draft_review_candidates',
        'retrieve_company_memory',
        'answer_with_rag',
    ]
    assert result.completed_nodes == workflow.node_names
    assert result.outputs['review_boundary'] == 'human_approval_required'
    assert result.outputs['retrieval_mode'] == 'vector_ready'
    assert result.outputs['orchestrator'] == 'rag_orchestrator_agent'
    assert result.outputs['token_budget_policy'] == 'delta_sync_hash_skip_evidence_budget'


def test_workflow_state_is_append_only_for_node_audit_trail() -> None:
    workflow = build_company_memory_workflow()
    state = AgentWorkflowState(objective='summarize_slack', inputs={'channel': 'proj-alpha'})

    result = workflow.run(state)

    assert state.completed_nodes == []
    assert result.completed_nodes == [
        'collect_evidence',
        'draft_review_candidates',
        'retrieve_company_memory',
        'answer_with_rag',
    ]


def test_company_memory_workflow_exposes_langgraph_topology() -> None:
    workflow = build_company_memory_workflow()

    assert workflow.node_names == [
        'collect_evidence',
        'draft_review_candidates',
        'retrieve_company_memory',
        'answer_with_rag',
    ]
    assert 'collect_evidence' in workflow.graph_mermaid
    assert 'answer_with_rag' in workflow.graph_mermaid
