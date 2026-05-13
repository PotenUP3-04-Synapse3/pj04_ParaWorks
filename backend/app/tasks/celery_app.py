from celery import Celery

from backend.app.core.config import Settings, get_settings


def build_celery_app(settings: Settings | None = None) -> Celery:
    selected = settings or get_settings()
    app = Celery(
        'paraworks',
        broker=selected.redis_url,
        backend=selected.redis_url,
        include=[
            'backend.app.tasks.rag_indexing',
            'backend.app.tasks.sync',
        ],
    )
    app.conf.update(
        task_always_eager=selected.celery_task_always_eager,
        task_eager_propagates=True,
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
    )
    # Configure periodic tasks (Celery Beat)
    app.conf.beat_schedule = {
        'periodic-google-drive-sync': {
            'task': 'sync.google_drive',
            'schedule': float(selected.google_drive_sync_interval_seconds),
        },
        'periodic-gmail-sync': {
            'task': 'sync.gmail',
            'schedule': float(selected.gmail_sync_interval_seconds),
        },
    }

    return app


celery_app = build_celery_app()
