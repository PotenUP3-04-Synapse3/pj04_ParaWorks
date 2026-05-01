from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.schemas.ask import AskRequest

router = APIRouter(prefix='/ask', tags=['ask'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


@router.post('')
def ask_company_memory(
    request: AskRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    answer = answer_question_with_rag(db=db, user=user, question=request.question)
    return {
        'agent_name': answer.agent_name,
        'prompt_version': answer.prompt_version,
        'question': answer.question,
        'answer': answer.answer,
        'source_links': answer.source_links,
        'source_snippets': answer.source_snippets,
        'permission_level': answer.permission_level,
        'hidden_match_count': answer.hidden_match_count,
        'permission_notice': answer.permission_notice,
        'cache_key': answer.cache_key,
        'model_name': answer.cost.model_name,
        'estimated_cost_usd': answer.cost.estimated_cost_usd,
        'token_usage': {
            'input_tokens': answer.cost.token_usage.input_tokens,
            'output_tokens': answer.cost.token_usage.output_tokens,
            'total_tokens': answer.cost.token_usage.total_tokens,
        },
    }
