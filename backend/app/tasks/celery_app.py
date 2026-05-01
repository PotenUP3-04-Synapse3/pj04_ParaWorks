from celery import Celery

from backend.app.core.config import Settings, get_settings


def build_celery_app(settings: Settings | None = None) -> Celery:
    selected = settings or get_settings()
    app = Celery(
        'paraworks',
        broker=selected.redis_url,
        backend=selected.redis_url,
        include=['backend.app.tasks.rag_indexing'],
    )
    app.conf.update(
        task_always_eager=selected.celery_task_always_eager,
        task_eager_propagates=True,
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
    )
    return app


celery_app = build_celery_app()
