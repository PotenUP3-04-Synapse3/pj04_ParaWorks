from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict


@dataclass(frozen=True)
class AgentWorkflowState:
    objective: str
    inputs: dict
    outputs: dict = field(default_factory=dict)
    completed_nodes: list[str] = field(default_factory=list)

    def complete_node(self, node_name: str, **outputs: str) -> 'AgentWorkflowState':
        return replace(
            self,
            outputs={**self.outputs, **outputs},
            completed_nodes=[*self.completed_nodes, node_name],
        )


WorkflowNode = Callable[[AgentWorkflowState], AgentWorkflowState]


class _LangGraphWorkflowState(TypedDict):
    objective: str
    inputs: dict
    outputs: dict
    completed_nodes: list[str]


@dataclass(frozen=True)
class AgentWorkflow:
    nodes: tuple[tuple[str, WorkflowNode], ...]
    compiled_graph: Any
    backend: str = 'langgraph'

    @property
    def node_names(self) -> list[str]:
        return [name for name, _node in self.nodes]

    @property
    def graph_mermaid(self) -> str:
        return self.compiled_graph.get_graph().draw_mermaid()

    def run(self, state: AgentWorkflowState) -> AgentWorkflowState:
        result = self.compiled_graph.invoke(
            {
                'objective': state.objective,
                'inputs': state.inputs,
                'outputs': state.outputs,
                'completed_nodes': state.completed_nodes,
            }
        )
        return AgentWorkflowState(
            objective=result['objective'],
            inputs=result['inputs'],
            outputs=result['outputs'],
            completed_nodes=result['completed_nodes'],
        )


def build_company_memory_workflow() -> AgentWorkflow:
    nodes = (
        ('collect_evidence', _collect_evidence),
        ('draft_review_candidates', _draft_review_candidates),
        ('retrieve_company_memory', _retrieve_company_memory),
        ('answer_with_rag', _answer_with_rag),
    )

    graph_builder = StateGraph(_LangGraphWorkflowState)
    for node_name, node in nodes:
        graph_builder.add_node(node_name, _as_langgraph_node(node))

    graph_builder.add_edge(START, nodes[0][0])
    for index in range(len(nodes) - 1):
        current_name = nodes[index][0]
        next_name = nodes[index + 1][0]
        graph_builder.add_edge(current_name, next_name)
    graph_builder.add_edge(nodes[-1][0], END)

    return AgentWorkflow(
        nodes=nodes,
        compiled_graph=graph_builder.compile(),
    )


def _as_langgraph_node(node: WorkflowNode) -> Callable[[_LangGraphWorkflowState], dict]:
    def run_node(state: _LangGraphWorkflowState) -> dict:
        result = node(
            AgentWorkflowState(
                objective=state['objective'],
                inputs=state['inputs'],
                outputs=state.get('outputs', {}),
                completed_nodes=state.get('completed_nodes', []),
            )
        )
        return {
            'outputs': result.outputs,
            'completed_nodes': result.completed_nodes,
        }

    return run_node


def _collect_evidence(state: AgentWorkflowState) -> AgentWorkflowState:
    return state.complete_node(
        'collect_evidence',
        evidence_sources='slack,gmail,drive,approved_knowledge',
        token_budget_policy='delta_sync_hash_skip_evidence_budget',
    )


def _draft_review_candidates(state: AgentWorkflowState) -> AgentWorkflowState:
    return state.complete_node(
        'draft_review_candidates',
        review_boundary='human_approval_required',
    )


def _retrieve_company_memory(state: AgentWorkflowState) -> AgentWorkflowState:
    return state.complete_node(
        'retrieve_company_memory',
        retrieval_mode='vector_ready',
    )


def _answer_with_rag(state: AgentWorkflowState) -> AgentWorkflowState:
    return state.complete_node(
        'answer_with_rag',
        orchestrator='rag_orchestrator_agent',
    )
