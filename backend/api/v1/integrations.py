from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.integration import Integration
from backend.schemas.admin import IntegrationStatusRead

log = structlog.get_logger(__name__)
router = APIRouter(prefix='/integrations', tags=['integrations'])

_VALID_TYPES = frozenset({'google_drive', 'gmail', 'slack', 'google_calendar'})


@router.get('', response_model=list[IntegrationStatusRead])
async def list_integrations(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
):
    result = await db.execute(
        select(Integration).where(Integration.organization_id == org_id)
    )
    return result.scalars().all()


@router.post('/{integration_type}/sync')
async def trigger_sync(
    integration_type: str,
    background_tasks: BackgroundTasks,
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
):
    if integration_type not in _VALID_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'지원하지 않는 통합 유형: {integration_type}')

    result = await db.execute(
        select(Integration).where(
            Integration.organization_id == org_id,
            Integration.type == integration_type,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        # 최초 연결 시 레코드 생성
        integration = Integration(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            type=integration_type,
            status='syncing',
        )
        db.add(integration)
    else:
        integration.status = 'syncing'

    job_id = str(uuid.uuid4())
    await db.commit()

    log.info('integration.sync_triggered', type=integration_type, org_id=org_id, job_id=job_id)
    # 실제 동기화는 백그라운드 태스크/Celery로 연결 (현재 stub)
    return {'job_id': job_id, 'status': 'syncing', 'integration_type': integration_type}


@router.delete('/{integration_type}', status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    integration_type: str,
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
):
    if integration_type not in _VALID_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    result = await db.execute(
        select(Integration).where(
            Integration.organization_id == org_id,
            Integration.type == integration_type,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    integration.status = 'disconnected'
    await db.commit()
