from collections.abc import Mapping

from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser
from backend.app.core.redaction import redact_secret_text
from backend.app.models import AuditLog


def record_audit_log(
    *,
    db: Session,
    actor: DemoUser,
    action: str,
    target_type: str,
    target_id: str | int | None = None,
    status: str = 'success',
    metadata: Mapping[str, object] | None = None,
) -> AuditLog:
    audit = AuditLog(
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        status=status,
        metadata_=_sanitize_metadata(metadata or {}),
    )
    db.add(audit)
    return audit


def serialize_audit_log(log: AuditLog) -> dict[str, object]:
    return {
        'id': log.id,
        'actor_id': log.actor_id,
        'actor_email': log.actor_email,
        'actor_role': log.actor_role,
        'action': log.action,
        'target_type': log.target_type,
        'target_id': log.target_id,
        'status': log.status,
        'metadata': log.metadata_ or {},
        'created_at': log.created_at.isoformat(),
    }


def _sanitize_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            sanitized[key] = redact_secret_text(value)
        elif isinstance(value, list):
            sanitized[key] = [redact_secret_text(item) if isinstance(item, str) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized
