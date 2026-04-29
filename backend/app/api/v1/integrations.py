"""Integrations routes — connect/disconnect OAuth services."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import encrypt_token
from app.models.integration import Integration, IntegrationStatus, ServiceType

router = APIRouter(prefix='/integrations', tags=['integrations'])


class IntegrationOut(BaseModel):
    id: UUID
    service_type: str
    status: str
    last_synced_at: Optional[str]

    model_config = {'from_attributes': True}


class ConnectIntegrationBody(BaseModel):
    service_type: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[str] = None
    metadata: Optional[dict] = None


@router.get('', response_model=List[IntegrationOut])
async def list_integrations(request: Request, db: AsyncSession = Depends(get_db)):
    org_id = request.state.org_id
    result = await db.execute(
        select(Integration).where(Integration.organization_id == org_id)
    )
    return result.scalars().all()


@router.post('', response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
async def connect_integration(
    body: ConnectIntegrationBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.org_id
    user_id = request.state.user_id

    try:
        service = ServiceType(body.service_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f'Unknown service type: {body.service_type}')

    # Check if already connected for this org
    existing = await db.execute(
        select(Integration).where(
            Integration.organization_id == org_id,
            Integration.service_type == service,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail='Integration already exists')

    integration = Integration(
        organization_id=org_id,
        user_id=user_id,
        service_type=service,
        access_token_encrypted=encrypt_token(body.access_token),
        refresh_token_encrypted=encrypt_token(body.refresh_token) if body.refresh_token else None,
        token_expiry=body.token_expiry,
        metadata_json=body.metadata or {},
        status=IntegrationStatus.active,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)

    # Trigger initial Drive sync if applicable
    if service == ServiceType.google_drive:
        from app.tasks.drive_tasks import initial_drive_sync
        initial_drive_sync.delay(str(integration.id))

    return integration


@router.delete('/{integration_id}', status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    integration_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.org_id
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.organization_id == org_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail='Integration not found')

    integration.status = IntegrationStatus.revoked
    await db.commit()
