from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agent_runtime import PermissionContext
from backend.app.agents.slack_agent import (
    DeterministicSlackAgentModel,
    SlackAgent,
    create_slack_agent_review_items,
)
from backend.app.connectors.mock import CONNECTOR_TYPES, get_mock_connector
from backend.app.db.session import get_db
from backend.app.ingestion.service import ingest_events
from backend.app.models import SyncJob

router = APIRouter(prefix='/integrations', tags=['integrations'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('')
def list_integrations() -> list[dict[str, str]]:
    return [
        {'type': source_type, 'mode': 'mock', 'status': 'ready'}
        for source_type in sorted(CONNECTOR_TYPES)
    ]


@router.post('/{connector_type}/sync')
def sync_connector(connector_type: str, db: DbSession) -> dict[str, int | str]:
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=404, detail='Connector not found')

    job = SyncJob(
        job_id=f'{connector_type}-{uuid4().hex}',
        connector_type=connector_type,
        status='running',
        message='sync running',
        progress_pct=10,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    connector = get_mock_connector(connector_type)
    created_review_items = ingest_events(db, connector.fetch_events())

    job.status = 'complete'
    job.message = 'sync complete'
    job.progress_pct = 100
    job.updated_at = datetime.now(UTC)
    db.commit()

    return {
        'job_id': job.job_id,
        'connector_type': connector_type,
        'status': job.status,
        'created_review_items': created_review_items,
    }


@router.post('/slack/agent-review')
def run_slack_agent_review(db: DbSession) -> dict[str, int | str]:
    agent = SlackAgent(model=DeterministicSlackAgentModel())
    review_items = create_slack_agent_review_items(
        db=db,
        agent=agent,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mock-slack:all',
    )

    return {
        'agent_name': 'slack_agent',
        'status': 'complete',
        'created_review_items': len(review_items),
    }
