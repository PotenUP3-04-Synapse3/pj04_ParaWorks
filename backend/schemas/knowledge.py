from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeAssetCreate(BaseModel):
    organization_id: str
    title: str = Field(..., min_length=1, max_length=500)
    summary: str | None = None
    asset_type: str = 'document'
    related_projects: list[str] | None = None
    related_departments: list[str] | None = None
    related_decisions: list[str] | None = None
    source_links: list[str] | None = None
    tags: list[str] | None = None
    permission_level: str = 'team'
    freshness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_external_client: bool = False
    external_data_policy: str | None = None


class KnowledgeAssetRead(KnowledgeAssetCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class HandoverPacketCreate(BaseModel):
    organization_id: str
    from_user_email: str
    to_user_email: str | None = None
    title: str = Field(..., min_length=1, max_length=500)
    summary: str | None = None
    related_projects: list[str] | None = None
    decision_record_ids: list[str] | None = None
    knowledge_asset_ids: list[str] | None = None
    key_contacts: list[dict] | None = None
    open_issues: list[dict] | None = None


class HandoverPacketRead(HandoverPacketCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
