from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import AgentRun

router = APIRouter(prefix='/agent-runs', tags=['agent-runs'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('')
def list_agent_runs(db: DbSession) -> dict:
    total_runs = db.scalar(select(func.count(AgentRun.id))) or 0
    total_tokens = db.scalar(select(func.coalesce(func.sum(AgentRun.total_tokens), 0))) or 0
    estimated_cost_usd = db.scalar(select(func.coalesce(func.sum(AgentRun.estimated_cost_usd), 0.0))) or 0.0
    recent_runs = db.scalars(select(AgentRun).order_by(AgentRun.id.desc()).limit(10)).all()

    return {
        'total_runs': total_runs,
        'total_tokens': total_tokens,
        'estimated_cost_usd': round(estimated_cost_usd, 6),
        'recent_runs': [
            {
                'id': run.id,
                'agent_name': run.agent_name,
                'prompt_version': run.prompt_version,
                'status': run.status,
                'source_window': run.source_window,
                'cache_key': run.cache_key,
                'model_name': run.model_name,
                'input_tokens': run.input_tokens,
                'output_tokens': run.output_tokens,
                'total_tokens': run.total_tokens,
                'estimated_cost_usd': round(run.estimated_cost_usd, 6),
                'permission_level': run.permission_level,
                'metadata': run.metadata_,
                'started_at': run.started_at.isoformat(),
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
            }
            for run in recent_runs
        ],
    }
