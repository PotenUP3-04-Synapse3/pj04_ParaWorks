from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agent_runtime import PermissionContext
from backend.app.agents.mail_document_agent import (
    DeterministicMailDocumentAgentModel,
    MailDocumentAgent,
    create_mail_document_agent_review_items,
)
from backend.app.agents.slack_agent import (
    DeterministicSlackAgentModel,
    SlackAgent,
    create_slack_agent_review_items,
)
from backend.app.connectors.mock import CONNECTOR_TYPES, get_mock_connector
from backend.app.connectors.registry import list_connector_manifests
from backend.app.db.session import get_db
from backend.app.ingestion.sync import sync_connector_events

router = APIRouter(prefix='/integrations', tags=['integrations'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('')
def list_integrations() -> list[dict[str, object]]:
    return [
        {
            'type': manifest.connector_type,
            'display_name': manifest.display_name,
            'mode': manifest.mode,
            'status': 'ready',
            'auth_type': manifest.auth_type,
            'required_scopes': list(manifest.required_scopes),
            'sync_strategy': manifest.sync_strategy,
            'cost_policy': manifest.cost_policy,
        }
        for manifest in list_connector_manifests()
    ]


@router.post('/{connector_type}/sync')
def sync_connector(connector_type: str, db: DbSession) -> dict[str, int | str]:
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=404, detail='Connector not found')

    connector = get_mock_connector(connector_type)
    result = sync_connector_events(db=db, connector=connector)

    return {
        'job_id': result.job_id,
        'connector_type': connector_type,
        'status': result.status,
        'created_review_items': result.created_review_items,
        'fetched_events': result.fetched_events,
        'skipped_events': result.skipped_events,
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


@router.post('/mail-docs/agent-review')
def run_mail_document_agent_review(db: DbSession) -> dict[str, int | str]:
    agent = MailDocumentAgent(model=DeterministicMailDocumentAgentModel())
    review_items = create_mail_document_agent_review_items(
        db=db,
        agent=agent,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mock-mail-docs:all',
    )

    return {
        'agent_name': 'mail_document_agent',
        'status': 'complete',
        'created_review_items': len(review_items),
    }
