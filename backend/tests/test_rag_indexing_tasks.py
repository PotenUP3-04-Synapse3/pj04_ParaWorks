from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.models import SyncJob
from backend.app.tasks.celery_app import build_celery_app
from backend.app.tasks.rag_indexing import execute_rag_reindex_job
from backend.tests.test_rag_indexing import seed_chunk

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_celery_app_uses_redis_and_eager_setting() -> None:
    settings = Settings(
        redis_url='redis://localhost:6379/5',
        celery_task_always_eager=True,
    )

    app = build_celery_app(settings)

    assert app.conf.broker_url == 'redis://localhost:6379/5'
    assert app.conf.result_backend == 'redis://localhost:6379/5'
    assert app.conf.task_always_eager is True


def test_execute_rag_reindex_job_updates_sync_job_status(db_session: Session) -> None:
    seed_chunk(db_session, 'Slack and Gmail history should be embedded for search.', 'gmail-task-index')
    job = SyncJob(
        job_id='rag-index-task-test',
        connector_type='rag-index',
        status='queued',
        message='queued',
        progress_pct=0,
    )
    db_session.add(job)
    db_session.commit()

    result = execute_rag_reindex_job(
        db=db_session,
        settings=Settings(database_url='sqlite://'),
        job_id=job.job_id,
        dry_run=True,
    )

    db_session.refresh(job)
    assert result['status'] == 'complete'
    assert result['indexed_count'] == 1
    assert job.status == 'complete'
    assert job.progress_pct == 100
    assert job.message == 'indexed=1 skipped=0 saved_embedding_calls=0'


def test_celery_worker_script_disables_eager_mode() -> None:
    script = (REPO_ROOT / 'scripts/start-celery-worker.ps1').read_text(encoding='utf-8')

    assert "$env:CELERY_TASK_ALWAYS_EAGER = 'false'" in script
    assert 'uv run celery -A backend.app.tasks.celery_app.celery_app worker' in script
    assert '--pool=solo' in script


def test_pgvector_dev_stack_supports_alternate_host_ports() -> None:
    script = (REPO_ROOT / 'scripts/start-pgvector-dev.ps1').read_text(encoding='utf-8')
    compose = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')

    assert '[int]$PostgresPort = 5432' in script
    assert '[int]$RedisPort = 6379' in script
    assert '$env:PARAWORKS_POSTGRES_PORT = "$PostgresPort"' in script
    assert '$env:PARAWORKS_REDIS_PORT = "$RedisPort"' in script
    assert '127.0.0.1:$PostgresPort/paraworks' in script
    assert '"127.0.0.1:${PARAWORKS_POSTGRES_PORT:-5432}:5432"' in compose
    assert '"127.0.0.1:${PARAWORKS_REDIS_PORT:-6379}:6379"' in compose
