from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.dependencies import CurrentUserId, DbSession
from backend.agents import extract_from_text, resume_extraction

router = APIRouter(prefix='/extraction', tags=['extraction'])


class ExtractionRequest(BaseModel):
    text: str
    org_id: str
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    decision: str  # 'approve' | 'reject'


@router.post('/start')
async def start_extraction(
    payload: ExtractionRequest,
    user_id: CurrentUserId,
):
    """텍스트에서 의사결정/지식자산 자동 추출 시작."""
    result = await extract_from_text(
        text=payload.text,
        organization_id=payload.org_id,
        user_id=user_id,
        thread_id=payload.thread_id,
    )
    return result


@router.post('/resume/{thread_id}')
async def resume(
    thread_id: str,
    payload: ResumeRequest,
    user_id: CurrentUserId,
):
    """HITL 승인/거부 후 추출 재개."""
    if payload.decision not in ('approve', 'reject'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='decision must be approve or reject')
    result = await resume_extraction(
        thread_id=thread_id,
        decision=payload.decision,
        checkpointer=None,
    )
    return result
