"""Celery application and task configuration."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    'paraworks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.ingestion_tasks',
        'app.tasks.drive_tasks',
        'app.tasks.audit_tasks',
        'app.tasks.slack_tasks',
    ],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    task_acks_late=True,          # Retry on worker crash
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
    beat_schedule={
        # Renew Google Drive watch channels every 5 days (channels expire after 7 days)
        'renew-drive-channels': {
            'task': 'app.tasks.drive_tasks.renew_all_drive_channels',
            'schedule': crontab(hour=2, minute=0),  # 02:00 daily
        },
        # Sync Gmail for all active integrations hourly
        'sync-gmail': {
            'task': 'app.tasks.ingestion_tasks.sync_all_gmail',
            'schedule': crontab(minute=30),  # every hour at :30
        },
        # Sync Calendar for all active integrations
        'sync-calendar': {
            'task': 'app.tasks.ingestion_tasks.sync_all_calendar',
            'schedule': crontab(minute=0),  # every hour
        },
    },
)
