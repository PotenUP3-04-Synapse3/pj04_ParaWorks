from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.agent_runtime import AgentWorkflowState, build_company_memory_workflow
from backend.app.agent_runtime.company_memory import (
    run_company_memory_agent_orchestration,
)
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db

router = APIRouter(prefix='/orchestration', tags=['orchestration'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


class CompanyMemoryDryRunRequest(BaseModel):
    objective: str = 'answer_from_company_memory'
    question: str = ''


class CompanyMemoryRunRequest(BaseModel):
    question: str = ''


def _cost_policy_response() -> dict:
    return {
        'delta_sync': True,
        'source_hash_skip': True,
        'evidence_token_budget': True,
        'paid_llm_calls_in_status_api': False,
        'requires_explicit_run': True,
    }


@router.get('/company-memory')
def get_company_memory_orchestration() -> dict:
    workflow = build_company_memory_workflow()

    return {
        'workflow_name': 'company_memory',
        'backend': workflow.backend,
        'node_names': workflow.node_names,
        'graph_mermaid': workflow.graph_mermaid,
        'cost_policy': _cost_policy_response(),
    }


@router.post('/company-memory/dry-run')
def dry_run_company_memory_orchestration(request: CompanyMemoryDryRunRequest) -> dict:
    workflow = build_company_memory_workflow()
    result = workflow.run(
        AgentWorkflowState(
            objective=request.objective,
            inputs={'question': request.question},
        )
    )

    return {
        'workflow_name': 'company_memory',
        'backend': workflow.backend,
        'objective': result.objective,
        'inputs': result.inputs,
        'completed_nodes': result.completed_nodes,
        'outputs': result.outputs,
        'token_cost_usd': 0,
        'cost_policy': _cost_policy_response(),
    }


@router.post('/company-memory/run')
def run_company_memory_orchestration(
    request: CompanyMemoryRunRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    result = run_company_memory_agent_orchestration(
        db=db,
        user=user,
        question=request.question,
    )

    return {
        'workflow_name': 'company_memory',
        'backend': result.backend,
        'completed_nodes': result.completed_nodes,
        'outputs': result.outputs,
        'cost_policy': _cost_policy_response(),
    }
