from collections.abc import Callable
from dataclasses import dataclass, field, replace


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


@dataclass(frozen=True)
class AgentWorkflow:
    nodes: tuple[tuple[str, WorkflowNode], ...]
    backend: str = 'local'

    @property
    def node_names(self) -> list[str]:
        return [name for name, _node in self.nodes]

    def run(self, state: AgentWorkflowState) -> AgentWorkflowState:
        current_state = state
        for _name, node in self.nodes:
            current_state = node(current_state)
        return current_state


def build_company_memory_workflow() -> AgentWorkflow:
    return AgentWorkflow(
        nodes=(
            ('collect_evidence', _collect_evidence),
            ('draft_review_candidates', _draft_review_candidates),
            ('retrieve_company_memory', _retrieve_company_memory),
            ('answer_with_rag', _answer_with_rag),
        )
    )


def _collect_evidence(state: AgentWorkflowState) -> AgentWorkflowState:
    return state.complete_node(
        'collect_evidence',
        evidence_sources='slack,gmail,drive,approved_knowledge',
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
