from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from backend.core.dependencies import CurrentUserId, DbSession
from backend.models.decision_record import DecisionRecord
from backend.schemas.decision import DecisionRecordCreate, DecisionRecordRead, DecisionRecordUpdate

router = APIRouter(prefix='/decisions', tags=['decisions'])


@router.get('', response_model=list[DecisionRecordRead])
async def list_decisions(
    db: DbSession,
    user_id: CurrentUserId,
    org_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[DecisionRecordRead]:
    result = await db.execute(
        select(DecisionRecord)
        .where(DecisionRecord.organization_id == org_id)
        .order_by(DecisionRecord.decided_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get('/{decision_id}', response_model=DecisionRecordRead)
async def get_decision(
    decision_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> DecisionRecordRead:
    record = await db.get(DecisionRecord, decision_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return record


@router.post('', response_model=DecisionRecordRead, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: DecisionRecordCreate,
    db: DbSession,
    user_id: CurrentUserId,
) -> DecisionRecordRead:
    record = DecisionRecord(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.patch('/{decision_id}', response_model=DecisionRecordRead)
async def update_decision(
    decision_id: str,
    payload: DecisionRecordUpdate,
    db: DbSession,
    user_id: CurrentUserId,
) -> DecisionRecordRead:
    record = await db.get(DecisionRecord, decision_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete('/{decision_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision(
    decision_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> None:
    record = await db.get(DecisionRecord, decision_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db.delete(record)
    await db.commit()
