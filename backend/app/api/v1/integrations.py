"""Integrations routes — connect/disconnect OAuth services."""
from __future__ import annotations

import json
import urllib.parse
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decrypt_token, encrypt_token
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


# ── Google OAuth (Drive / Gmail / Calendar) ───────────────────────────────────

# service_type → 필요한 OAuth 스코프 매핑
_GOOGLE_SCOPES: dict[str, list[str]] = {
    'google_drive': [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
    ],
    'gmail': [
        'https://www.googleapis.com/auth/gmail.readonly',
    ],
    'google_calendar': [
        'https://www.googleapis.com/auth/calendar.readonly',
    ],
}


@router.get('/google/authorize')
async def google_authorize(service: str, request: Request):
    """Google OAuth2 인증 URL을 반환한다.

    Query params:
        service: google_drive | gmail | google_calendar
    """
    if service not in _GOOGLE_SCOPES:
        raise HTTPException(status_code=400, detail=f'지원하지 않는 서비스: {service}')

    org_id = str(request.state.org_id)
    user_id = str(request.state.user_id)

    # state에 org_id, user_id, service 묶어서 전달 (CSRF 방지 포함)
    state_payload = json.dumps({'org_id': org_id, 'user_id': user_id, 'service': service})

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_INTEGRATION_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(_GOOGLE_SCOPES[service]),
        'access_type': 'offline',
        'prompt': 'consent',  # 항상 refresh_token 받도록
        'state': state_payload,
    }
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
    return {'url': url}


@router.get('/google/callback')
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth2 콜백 — code를 토큰으로 교환하고 Integration을 저장한다."""
    if error:
        return RedirectResponse(
            url=f'{settings.FRONTEND_URL}/integrations?error={urllib.parse.quote(error)}'
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail='code 또는 state 누락')

    try:
        state_data = json.loads(state)
        org_id = UUID(state_data['org_id'])
        user_id = UUID(state_data['user_id'])
        service_str = state_data['service']
    except Exception:
        raise HTTPException(status_code=400, detail='state 파라미터가 올바르지 않습니다')

    if service_str not in _GOOGLE_SCOPES:
        raise HTTPException(status_code=400, detail=f'지원하지 않는 서비스: {service_str}')

    # code → access_token + refresh_token 교환
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': settings.GOOGLE_INTEGRATION_REDIRECT_URI,
                'grant_type': 'authorization_code',
            },
        )
    token_data = resp.json()

    if 'error' in token_data:
        return RedirectResponse(
            url=f'{settings.FRONTEND_URL}/integrations?error={urllib.parse.quote(token_data["error"])}'
        )

    access_token = token_data.get('access_token', '')
    refresh_token = token_data.get('refresh_token', '')
    expires_in = token_data.get('expires_in', 3600)

    service = ServiceType(service_str)

    # 기존 연동이 있으면 토큰 업데이트, 없으면 신규 생성
    result = await db.execute(
        select(Integration).where(
            Integration.organization_id == org_id,
            Integration.service_type == service,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token_encrypted = encrypt_token(access_token)
        if refresh_token:
            existing.refresh_token_encrypted = encrypt_token(refresh_token)
        existing.status = IntegrationStatus.active
    else:
        new_intg = Integration(
            organization_id=org_id,
            user_id=user_id,
            service_type=service,
            access_token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
            metadata_json={'expires_in': expires_in},
            status=IntegrationStatus.active,
        )
        db.add(new_intg)

    await db.commit()

    # Google Drive 초기 동기화 트리거
    if service == ServiceType.google_drive:
        result2 = await db.execute(
            select(Integration).where(
                Integration.organization_id == org_id,
                Integration.service_type == service,
            )
        )
        intg = result2.scalar_one_or_none()
        if intg:
            from app.tasks.drive_tasks import initial_drive_sync
            initial_drive_sync.delay(str(intg.id))

    return RedirectResponse(
        url=f'{settings.FRONTEND_URL}/integrations?connected={service_str}'
    )
