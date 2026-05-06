from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, require_admin_user
from backend.app.db.session import get_db
from backend.app.models import AgentRun

router = APIRouter(prefix='/agent-runs', tags=['agent-runs'])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]


def _agent_run_response(run: AgentRun) -> dict:
    metadata = run.metadata_ or {}
    return {
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
        'token_usage': {
            'input_tokens': run.input_tokens,
            'output_tokens': run.output_tokens,
            'total_tokens': run.total_tokens,
        },
        'estimated_cost_usd': round(run.estimated_cost_usd, 6),
        'permission_level': run.permission_level,
        'metadata': metadata,
        'selection_strategy': metadata.get('selection_strategy'),
        'evidence_summary': metadata.get('evidence_summary', []),
        'started_at': run.started_at.isoformat(),
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get('')
def list_agent_runs(db: DbSession, _: AdminUser) -> dict:
    total_runs = db.scalar(select(func.count(AgentRun.id))) or 0
    total_tokens = db.scalar(select(func.coalesce(func.sum(AgentRun.total_tokens), 0))) or 0
    estimated_cost_usd = db.scalar(select(func.coalesce(func.sum(AgentRun.estimated_cost_usd), 0.0))) or 0.0
    recent_runs = db.scalars(select(AgentRun).order_by(AgentRun.id.desc()).limit(10)).all()

    return {
        'total_runs': total_runs,
        'total_tokens': total_tokens,
        'estimated_cost_usd': round(estimated_cost_usd, 6),
        'recent_runs': [_agent_run_response(run) for run in recent_runs],
    }


@router.get('/summary')
def summarize_agent_runs(db: DbSession, _: AdminUser) -> dict:
    runs = db.scalars(select(AgentRun).order_by(AgentRun.id.desc())).all()
    total_runs = len(runs)
    total_tokens = sum(run.total_tokens for run in runs)
    estimated_cost_usd = sum(run.estimated_cost_usd for run in runs)
    cache_hits = sum(1 for run in runs if run.metadata_.get('cache_hit') is True)
    by_status: dict[str, int] = {}
    by_agent: dict[str, dict] = {}

    for run in runs:
        by_status[run.status] = by_status.get(run.status, 0) + 1
        agent_summary = by_agent.setdefault(
            run.agent_name,
            {
                'agent_name': run.agent_name,
                'run_count': 0,
                'total_tokens': 0,
                'estimated_cost_usd': 0.0,
                'latest_run_id': run.id,
                'latest_status': run.status,
            },
        )
        agent_summary['run_count'] += 1
        agent_summary['total_tokens'] += run.total_tokens
        agent_summary['estimated_cost_usd'] += run.estimated_cost_usd

    agent_rows = []
    for agent_summary in by_agent.values():
        run_count = agent_summary['run_count']
        agent_rows.append(
            {
                **agent_summary,
                'estimated_cost_usd': round(agent_summary['estimated_cost_usd'], 6),
                'average_tokens_per_run': round(agent_summary['total_tokens'] / run_count) if run_count else 0,
            }
        )

    return {
        'totals': {
            'total_runs': total_runs,
            'total_tokens': total_tokens,
            'estimated_cost_usd': round(estimated_cost_usd, 6),
            'average_tokens_per_run': round(total_tokens / total_runs) if total_runs else 0,
            'average_cost_per_run': round(estimated_cost_usd / total_runs, 6) if total_runs else 0,
            'cache_hits': cache_hits,
            'cache_hit_rate': round(cache_hits / total_runs, 4) if total_runs else 0,
        },
        'by_status': by_status,
        'by_agent': sorted(agent_rows, key=lambda item: item['estimated_cost_usd'], reverse=True),
    }


@router.get('/{run_id}')
def get_agent_run(run_id: int, db: DbSession, _: AdminUser) -> dict:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='Agent run not found')
    return _agent_run_response(run)
