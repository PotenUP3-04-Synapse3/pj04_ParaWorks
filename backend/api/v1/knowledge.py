from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.knowledge_asset import KnowledgeAsset
from backend.models.patterns import HandoverPacket
from backend.schemas.knowledge import (
    HandoverPacketCreate,
    HandoverPacketRead,
    KnowledgeAssetCreate,
    KnowledgeAssetRead,
)
from backend.agents import generate_handover_packet

router = APIRouter(prefix='/knowledge', tags=['knowledge'])


# ---- Knowledge Assets ----

@router.get('/assets', response_model=list[KnowledgeAssetRead])
async def list_assets(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(KnowledgeAsset)
        .where(KnowledgeAsset.organization_id == org_id)
        .order_by(KnowledgeAsset.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get('/assets/{asset_id}', response_model=KnowledgeAssetRead)
async def get_asset(asset_id: str, db: DbSession, user_id: CurrentUserId):
    asset = await db.get(KnowledgeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return asset


@router.post('/assets', response_model=KnowledgeAssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(payload: KnowledgeAssetCreate, db: DbSession, user_id: CurrentUserId):
    asset = KnowledgeAsset(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


# ---- Handover Packets ----

@router.post('/handover', response_model=dict)
async def create_handover(
    payload: HandoverPacketCreate,
    db: DbSession,
    user_id: CurrentUserId,
):
    """AI 기반 인수인계 패키지 자동 생성."""
    result = await generate_handover_packet(
        user_id=payload.from_user_id,
        organization_id=payload.organization_id,
        additional_context=payload.notes or '',
    )
    packet = HandoverPacket(id=str(uuid.uuid4()), **result.model_dump())
    db.add(packet)
    await db.commit()
    await db.refresh(packet)
    return {'id': packet.id, 'status': 'created'}


@router.get('/handover/{packet_id}', response_model=HandoverPacketRead)
async def get_handover(packet_id: str, db: DbSession, user_id: CurrentUserId):
    packet = await db.get(HandoverPacket, packet_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return packet
