from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import (
    AgentWorkflowState,
    PermissionContext,
    TokenUsage,
    build_agent_workflow,
    evaluate_agent_cost_budget,
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

DEFAULT_AGENT_RUN_BUDGET_USD = 0.001
DEFAULT_INPUT_COST_PER_1M = 0.15
DEFAULT_OUTPUT_COST_PER_1M = 0.60
DEFAULT_ESTIMATED_OUTPUT_TOKENS = 32


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
    cost_plan = build_company_memory_cost_plan(db=db, question=question)
    workflow = build_agent_workflow(
        (
            ('collect_evidence', _collect_evidence_node(db, cost_plan)),
            ('draft_review_candidates', _draft_review_candidates_node(db, permission_context, cost_plan)),
            ('retrieve_company_memory', _retrieve_company_memory_node()),
            ('answer_with_rag', _answer_with_rag_node(db, user, question, cost_plan)),
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


def build_company_memory_cost_plan(*, db: Session, question: str) -> dict[str, dict[str, float | int | str | None]]:
    slack_token_estimate = _estimate_tokens_for_sources(db=db, source_types=('slack',))
    mail_document_token_estimate = _estimate_tokens_for_sources(db=db, source_types=('gmail', 'drive'))
    question_token_estimate = _estimate_tokens(question)

    return {
        'slack_agent': _agent_cost_plan(
            has_input=slack_token_estimate > 0,
            run_reason='slack_evidence_available',
            skip_reason='no_slack_evidence',
            estimated_input_tokens=slack_token_estimate,
        ),
        'mail_document_agent': _agent_cost_plan(
            has_input=mail_document_token_estimate > 0,
            run_reason='mail_document_evidence_available',
            skip_reason='no_mail_document_evidence',
            estimated_input_tokens=mail_document_token_estimate,
        ),
        'rag_orchestrator_agent': _agent_cost_plan(
            has_input=question_token_estimate > 0,
            run_reason='question_provided',
            skip_reason='empty_question',
            estimated_input_tokens=question_token_estimate,
        ),
    }


def _collect_evidence_node(db: Session, cost_plan: dict[str, dict[str, float | int | str | None]]):
    def collect_evidence(state: AgentWorkflowState) -> AgentWorkflowState:
        slack_count = _count_chunks(db=db, source_types=('slack',))
        mail_document_count = _count_chunks(db=db, source_types=('gmail', 'drive'))
        return state.complete_node(
            'collect_evidence',
            evidence_sources='slack,gmail,drive,approved_knowledge',
            slack_evidence_count=slack_count,
            mail_document_evidence_count=mail_document_count,
            token_budget_policy='delta_sync_hash_skip_evidence_budget',
            cost_plan=cost_plan,
        )

    return collect_evidence


def _draft_review_candidates_node(
    db: Session,
    permission_context: PermissionContext,
    cost_plan: dict[str, dict[str, float | int | str | None]],
):
    def draft_review_candidates(state: AgentWorkflowState) -> AgentWorkflowState:
        slack_items = []
        if cost_plan['slack_agent']['action'] == 'run':
            slack_items = create_slack_agent_review_items(
                db=db,
                agent=SlackAgent(model=DeterministicSlackAgentModel()),
                permission_context=permission_context,
                source_window='orchestrated-slack:all',
            )
        mail_document_items = []
        if cost_plan['mail_document_agent']['action'] == 'run':
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


def _answer_with_rag_node(
    db: Session,
    user: DemoUser,
    question: str,
    cost_plan: dict[str, dict[str, float | int | str | None]],
):
    def answer_with_rag(state: AgentWorkflowState) -> AgentWorkflowState:
        if cost_plan['rag_orchestrator_agent']['action'] == 'skip':
            return state.complete_node(
                'answer_with_rag',
                orchestrator='rag_orchestrator_agent',
                rag_agent_run_created=False,
            )
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


def _estimate_tokens_for_sources(*, db: Session, source_types: tuple[str, ...]) -> int:
    rows = db.scalars(
        select(DocumentChunk.text)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type.in_(source_types))
    ).all()
    return sum(_estimate_tokens(text) for text in rows)


def _estimate_tokens(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 4)


def _agent_cost_plan(
    *,
    has_input: bool,
    run_reason: str,
    skip_reason: str,
    estimated_input_tokens: int,
) -> dict[str, float | int | str | None]:
    if not has_input:
        return {
            'action': 'skip',
            'reason': skip_reason,
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_output_tokens': 0,
            'estimated_cost_usd': 0.0,
            'budget_limit_usd': DEFAULT_AGENT_RUN_BUDGET_USD,
            'budget_status': 'no_input',
        }

    decision = evaluate_agent_cost_budget(
        model_name='planning-estimate',
        token_usage=TokenUsage(
            input_tokens=estimated_input_tokens,
            output_tokens=DEFAULT_ESTIMATED_OUTPUT_TOKENS,
        ),
        input_cost_per_1m=DEFAULT_INPUT_COST_PER_1M,
        output_cost_per_1m=DEFAULT_OUTPUT_COST_PER_1M,
        max_cost_usd=DEFAULT_AGENT_RUN_BUDGET_USD,
        cache_hit=False,
    )

    return {
        'action': decision.action,
        'reason': run_reason if decision.action == 'run' else decision.reason,
        'estimated_input_tokens': estimated_input_tokens,
        'estimated_output_tokens': DEFAULT_ESTIMATED_OUTPUT_TOKENS,
        'estimated_cost_usd': round(decision.estimated_cost_usd, 6),
        'budget_limit_usd': decision.budget_limit_usd,
        'budget_status': decision.budget_status,
    }
