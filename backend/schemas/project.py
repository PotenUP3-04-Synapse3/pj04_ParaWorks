from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    organization_id: str
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    status: str = 'active'
    owner_id: str | None = None
    department_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    owner_id: str | None = None
    department_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
