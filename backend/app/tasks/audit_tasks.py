"""Celery task for audit log recording (called from middleware)."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def record_audit_log(
    self,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    resource_path: str,
    ip_addr: str,
    user_agent: str,
    status_code: int,
) -> None:
    """Persist an audit log entry to the database."""
    async def _do():
        from app.core.database import get_db_context
        from app.models.audit_log import AuditLog

        async with get_db_context() as db:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_path=resource_path,
                ip_addr=ip_addr,
                user_agent=user_agent,
                status_code=status_code,
            )
            db.add(log)
            await db.commit()

    try:
        _run(_do())
    except Exception as exc:
        logger.exception('record_audit_log failed: %s', exc)
        raise self.retry(exc=exc)
