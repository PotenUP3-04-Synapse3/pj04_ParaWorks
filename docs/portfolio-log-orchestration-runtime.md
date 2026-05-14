# ParaWorks Orchestration and Agent Runtime Portfolio Log

Last updated: 2026-05-11

This file records the core orchestration logic, agent runtime contracts, and operational policies that power the ParaWorks multi-agent system.

## Shared Agent Contracts

### Agent Runtime Contracts and Registry

Recorded on 2026-05-11.

Established the foundation for the "Equal Agent Ownership Model" by defining shared payloads and a central registry.

- **Shared Concepts**: Implemented `AgentInput`, `AgentOutput`, `EvidencePacket`, `ReviewCandidate`, and `AgentManifest` in `backend/app/agent_runtime/contracts.py`.
- **Central Registry**: Added `AgentRegistry` in `backend/app/agent_runtime/registry.py` to allow dynamic discovery of agent capabilities without direct imports between feature agents.
- **Evidence-First Rule**: Enforced mandatory source links, snippets, and confidence scores for all `ReviewCandidate` objects.

Portfolio angle:

- Shows high-quality software engineering with decoupled agent architectures.
- Enables multiple developers/agents to work on separate tracks (Slack, Mail, RAG) while sharing a stable runtime contract.

## Agent Orchestration

### LangGraph Workflow Orchestration

Recorded on 2026-05-11.

Implemented the primary orchestration engine using LangGraph to manage complex agentic workflows.

- **State Management**: Defined `AgentWorkflowState` to track objectives, inputs, outputs, and completed nodes across the graph.
- **Node Execution**: Implemented sequential and conditional node execution in `backend/app/agent_runtime/orchestration.py`.
- **Company Memory Workflow**: Built the default `collect_evidence -> draft_review_candidates -> retrieve_company_memory -> answer_with_rag` graph.

Portfolio angle:

- Demonstrates advanced LLM orchestration using industry-standard tools (LangGraph).
- Makes the reasoning process of the system observable and testable at each node.

## Operational Policies

### Token Cost and Budget Policy

Recorded on 2026-05-11.

Implemented proactive cost controls to manage LLM API usage and provide operator visibility.

- **Cost Estimation**: Added `backend/app/agent_runtime/cost_policy.py` to estimate USD cost based on token usage and model-specific pricing.
- **Evidence Hash Caching**: Implemented deterministic caching of agent outputs based on a hash of the `EvidencePacket` and `prompt_version`.
- **Budget Guards**: Added `AgentCostBudgetDecision` to allow the system to skip expensive agent runs if they exceed a configured threshold or result in a cache hit.

Portfolio angle:

- Addresses a critical production requirement: cost control.
- Demonstrates how to build efficient AI systems that avoid redundant computation and API calls.
