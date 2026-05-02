from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, require_admin_user
from backend.app.db.session import get_db
from backend.app.models import AuditLog
from backend.app.services.audit import serialize_audit_log

router = APIRouter(prefix='/admin', tags=['admin'])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]


@router.get('/audit-logs')
def list_audit_logs(db: DbSession, _: AdminUser, limit: int = 50) -> dict[str, list[dict[str, object]]]:
    safe_limit = max(1, min(limit, 100))
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(safe_limit)).all()
    return {'logs': [serialize_audit_log(log) for log in logs]}
