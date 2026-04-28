from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DecisionParticipantSchema(BaseModel):
    user_email: str
    role: str | None = None


class EvidenceSourceSchema(BaseModel):
    source_type: str
    source_id: str | None = None
    source_url: str | None = None
    snippet: str | None = None


class DecisionRecordCreate(BaseModel):
    organization_id: str
    related_project_id: str | None = None
    related_department_id: str | None = None
    business_domain: str | None = None
    title: str = Field(..., min_length=1, max_length=500)
    decision_summary: str
    situation: str | None = None
    reason: str | None = None
    alternatives_considered: list[str] | None = None
    constraints: str | None = None
    final_decision: str
    decision_maker: str | None = None
    participants: list[str] | None = None
    decided_at: datetime | None = None
    source_links: list[str] | None = None
    source_snippets: list[dict] | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    permission_level: str = 'team'
    review_status: str = 'pending'


class DecisionRecordRead(DecisionRecordCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    participants_detail: list[DecisionParticipantSchema] = Field(default_factory=list)
    evidence_sources: list[EvidenceSourceSchema] = Field(default_factory=list)

    model_config = {'from_attributes': True}


class DecisionRecordUpdate(BaseModel):
    title: str | None = None
    decision_summary: str | None = None
    situation: str | None = None
    reason: str | None = None
    alternatives_considered: list[str] | None = None
    constraints: str | None = None
    final_decision: str | None = None
    confidence_score: float | None = None
    review_status: str | None = None
    permission_level: str | None = None
