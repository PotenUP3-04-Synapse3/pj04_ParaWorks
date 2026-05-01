from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import (
    AgentWorkflowState,
    PermissionContext,
    build_agent_workflow,
)
from backend.app.agents.mail_document_agent import (
    DeterministicMailDocumentAgentModel,
    MailDocumentAgent,
    create_mail_document_agent_review_items,
)
from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.agents.slack_agent import (
    DeterministicSlackAgentModel,
    SlackAgent,
    create_slack_agent_review_items,
)
from backend.app.core.demo_auth import DemoUser
from backend.app.models import DocumentChunk, Source


@dataclass(frozen=True)
class CompanyMemoryOrchestrationResult:
    backend: str
    completed_nodes: list[str]
    outputs: dict


def run_company_memory_agent_orchestration(
    *,
    db: Session,
    user: DemoUser,
    question: str,
) -> CompanyMemoryOrchestrationResult:
    permission_context = PermissionContext(user_id=user.id, role=user.role)
    workflow = build_agent_workflow(
        (
            ('collect_evidence', _collect_evidence_node(db)),
            ('draft_review_candidates', _draft_review_candidates_node(db, permission_context)),
            ('retrieve_company_memory', _retrieve_company_memory_node()),
            ('answer_with_rag', _answer_with_rag_node(db, user, question)),
        )
    )
    result = workflow.run(
        AgentWorkflowState(
            objective='company_memory_agent_orchestration',
            inputs={'question': question, 'user_id': user.id},
        )
    )

    return CompanyMemoryOrchestrationResult(
        backend=workflow.backend,
        completed_nodes=result.completed_nodes,
        outputs=result.outputs,
    )


def _collect_evidence_node(db: Session):
    def collect_evidence(state: AgentWorkflowState) -> AgentWorkflowState:
        slack_count = _count_chunks(db=db, source_types=('slack',))
        mail_document_count = _count_chunks(db=db, source_types=('gmail', 'drive'))
        return state.complete_node(
            'collect_evidence',
            evidence_sources='slack,gmail,drive,approved_knowledge',
            slack_evidence_count=slack_count,
            mail_document_evidence_count=mail_document_count,
            token_budget_policy='delta_sync_hash_skip_evidence_budget',
        )

    return collect_evidence


def _draft_review_candidates_node(db: Session, permission_context: PermissionContext):
    def draft_review_candidates(state: AgentWorkflowState) -> AgentWorkflowState:
        slack_items = create_slack_agent_review_items(
            db=db,
            agent=SlackAgent(model=DeterministicSlackAgentModel()),
            permission_context=permission_context,
            source_window='orchestrated-slack:all',
        )
        mail_document_items = create_mail_document_agent_review_items(
            db=db,
            agent=MailDocumentAgent(model=DeterministicMailDocumentAgentModel()),
            permission_context=permission_context,
            source_window='orchestrated-mail-docs:all',
        )
        return state.complete_node(
            'draft_review_candidates',
            review_boundary='human_approval_required',
            slack_review_items_created=len(slack_items),
            mail_document_review_items_created=len(mail_document_items),
        )

    return draft_review_candidates


def _retrieve_company_memory_node():
    def retrieve_company_memory(state: AgentWorkflowState) -> AgentWorkflowState:
        return state.complete_node(
            'retrieve_company_memory',
            retrieval_mode='vector_ready',
        )

    return retrieve_company_memory


def _answer_with_rag_node(db: Session, user: DemoUser, question: str):
    def answer_with_rag(state: AgentWorkflowState) -> AgentWorkflowState:
        answer_question_with_rag(db=db, user=user, question=question)
        return state.complete_node(
            'answer_with_rag',
            orchestrator='rag_orchestrator_agent',
            rag_agent_run_created=True,
        )

    return answer_with_rag


def _count_chunks(*, db: Session, source_types: tuple[str, ...]) -> int:
    return (
        db.scalar(
            select(func.count(DocumentChunk.id))
            .join(Source, DocumentChunk.source_id == Source.id)
            .where(Source.source_type.in_(source_types))
        )
        or 0
    )
