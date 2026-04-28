from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    type: str
    title: str
    body: str | None = None
    link: str | None = None
    is_read: bool
    payload: dict | None = None
    created_at: datetime


class IntegrationStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    type: str
    status: str
    last_synced_at: str | None = None
    next_sync_at: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    actor_id: str | None = None
    actor_email: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    created_at: datetime
